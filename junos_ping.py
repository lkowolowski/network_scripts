#!/usr/bin/env -S uv run --script
# /// script
# requires-python = "==3.12.*"
# dependencies = [
#  "junos-eznc",
#  "lxml",
# ]
# ///

# © Louis Kowolowski 2025
#
# For python 3.13+, you need to install
# pip install telnetlib-313-and-up
# until junos-eznc gets updated
#
import argparse
import json
import subprocess
import sys
from io import StringIO

from jnpr.junos import Device
from jnpr.junos.exception import (
    ConnectAuthError,
    ConnectError,
    ConnectRefusedError,
    ConnectTimeoutError,
)
from lxml import etree


def _escape_lp(value: str) -> str:
    escaped = str(value).replace("\\", "\\\\")
    escaped = escaped.replace(" ", "\\ ")
    escaped = escaped.replace(",", "\\,")
    escaped = escaped.replace("=", "\\=")
    return escaped


def _find_int(root, tag: str):
    text = root.findtext(f".//{tag}")
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def _microseconds_to_seconds(value):
    if value is None:
        return None
    return value / 1_000_000


def _escape_field_string(value: str) -> str:
    escaped = str(value).replace("\\", "\\\\")
    return escaped.replace('"', '\\"')


def _emit_metrics(device, target, routing_instance, fields, output_format):
    tags = {
        "device": device,
        "target": target,
        "vrf": routing_instance,
    }
    if output_format == "json":
        payload = {
            "measurement": "junos_ping",
            "tags": tags,
            "fields": {k: v for k, v in fields.items() if v is not None},
        }
        print(json.dumps(payload))
        return

    measurement = _escape_lp("junos_ping")
    tag_str = ",".join(f"{_escape_lp(k)}={_escape_lp(v)}" for k, v in tags.items())

    field_parts = []
    for key, value in fields.items():
        if value is None:
            continue
        field_key = _escape_lp(key)
        if isinstance(value, int):
            field_parts.append(f"{field_key}={value}i")
        elif isinstance(value, float):
            field_parts.append(f"{field_key}={value}")
        else:
            field_parts.append(f'{field_key}="{_escape_field_string(value)}"')

    if field_parts:
        print(f"{measurement},{tag_str} {','.join(field_parts)}")


def main():
    """main"""

    parser = argparse.ArgumentParser(description="Execute a ping from a Junos device using NETCONF")
    parser.add_argument(
        "-d",
        "--device",
        required=True,
        help="Juniper device (hostname or IP) to source the ping from",
    )
    parser.add_argument("-t", "--target", required=True, help="Target IP address to ping")
    parser.add_argument(
        "-c",
        "--count",
        type=int,
        default=1,
        help="Number of pings to send (default: 1)",
    )
    parser.add_argument(
        "-i",
        "--vrf",
        default="default",
        help="VRF / routing-instance to use (default: default)",
    )
    parser.add_argument(
        "-u",
        "--username",
        default="automation",
        help="Username to connect as (default: automation)",
    )
    parser.add_argument(
        "-k",
        "--ssh-key",
        help="Path to SSH private key for authentication",
    )
    parser.add_argument(
        "-o",
        "--output-format",
        choices=("line", "json"),
        default="line",
        help="Telegraf output format for stdout (default: line protocol)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print human-readable connection logs to stderr",
    )
    args = parser.parse_args()

    device = args.device
    target = args.target
    if args.count <= 0:
        raise ValueError("Ping count must be greater than zero")

    count = args.count
    routing_instance = args.vrf
    username = args.username
    output_format = args.output_format
    verbose = args.verbose

    # open a connection to the device and start a NETCONF session
    try:
        subprocess.run(
            ["ping", "-qc", "1", device],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except subprocess.CalledProcessError:
        print(
            f"ERROR: Unable to reach {device} via system ping. Aborting.",
            file=sys.stderr,
        )
        _emit_metrics(
            device,
            target,
            routing_instance,
            {
                "packets_sent": 0,
                "packets_received": 0,
                "success": 0,
                "error": "local_ping_failed",
            },
            output_format,
        )
        return

    try:
        connect_kwargs = {"host": device, "user": username, "gather_facts": False}
        if args.ssh_key:
            connect_kwargs["ssh_private_key_file"] = args.ssh_key
        with Device(**connect_kwargs) as dev:
            # needed for file compression on srx340 because they are slow
            dev.timeout = 120
            dev.banner_timeout = 60  # pyright: ignore[reportAttributeAccessIssue]

            if verbose:
                print(f"Connected successfully to {device}", file=sys.stderr)
                print(
                    f"Pinging device {target} from {routing_instance}",
                    file=sys.stderr,
                )

            ping_params = {
                "count": str(count),
                "host": target,
                "normalize": True,
            }
            if routing_instance != "default":
                ping_params["instance"] = routing_instance

            ping_result = dev.rpc.ping(**ping_params)

            ping_result_str = etree.tostring(ping_result, encoding="unicode")

            f = StringIO(ping_result_str)
            context = etree.parse(f)
            root = context.getroot()
            probes_sent_val = _find_int(root, "probes-sent")
            responses_received_val = _find_int(root, "responses-received")
            packet_loss = _find_int(root, "packet-loss")

            rtt_min_seconds = _microseconds_to_seconds(_find_int(root, "rtt-minimum"))
            rtt_max_seconds = _microseconds_to_seconds(_find_int(root, "rtt-maximum"))
            rtt_avg_seconds = _microseconds_to_seconds(_find_int(root, "rtt-average"))
            rtt_stddev_seconds = _microseconds_to_seconds(_find_int(root, "rtt-stddev"))

            probes_sent = probes_sent_val if probes_sent_val is not None else 0
            responses_received = responses_received_val if responses_received_val is not None else 0
            success = 1 if responses_received > 0 else 0

            fields = {
                "packets_sent": probes_sent,
                "packets_received": responses_received,
                "success": success,
                "packet_loss": packet_loss,
                "rtt_min_seconds": rtt_min_seconds,
                "rtt_max_seconds": rtt_max_seconds,
                "rtt_avg_seconds": rtt_avg_seconds,
                "rtt_stddev_seconds": rtt_stddev_seconds,
            }
            if success == 0:
                fields["error"] = "no_responses"

            _emit_metrics(device, target, routing_instance, fields, output_format)
    except (
        ConnectAuthError,
        ConnectRefusedError,
        ConnectTimeoutError,
        ConnectError,
    ) as err:
        print(
            f"ERROR: Connection failed ({err.__class__.__name__}): {err}",
            file=sys.stderr,
        )
        _emit_metrics(
            device,
            target,
            routing_instance,
            {
                "packets_sent": 0,
                "packets_received": 0,
                "success": 0,
                "error": err.__class__.__name__,
            },
            output_format,
        )
        return

    if verbose:
        print("Connection closed...", file=sys.stderr)


if __name__ == "__main__":
    main()
