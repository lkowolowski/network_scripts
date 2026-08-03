#!/usr/bin/env -S uv run --script
# /// script
# requires-python = "==3.12.*"
# dependencies = [
#  "junos-eznc",
# ]
# ///

# © Louis Kowolowski 2023
#
# For python 3.13+, you need to install
# pip install telnetlib-313-and-up
# until junos-eznc gets updated
#
import argparse
import datetime
import os
import time
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from typing import cast

from jnpr.junos import Device
from jnpr.junos.exception import ConnectError, RpcError
from jnpr.junos.utils.fs import FS
from jnpr.junos.utils.scp import SCP
from jnpr.junos.utils.start_shell import StartShell
from lxml import etree

SLEEP_LONG = 30
SLEEP_SHORT = 10

Command = tuple[str, int | None]

SLEEP_LONG = 30
SLEEP_SHORT = 10


@contextmanager
def start_shell(dev: Device) -> Iterator[StartShell]:
    """StartShell wrapper that degrades gracefully if the device drops the session"""

    try:
        with StartShell(dev) as ss:
            yield ss
    except (EOFError, OSError) as err:
        print(f"WARNING: device dropped the shell session: {err}")


def delete_file(dev: Device, file: str) -> None:
    """delete a file"""
    file_system = FS(dev)
    file_stat = file_system.stat(file)
    if file_stat is None or file_stat["size"] is None:
        print(f"File {file} does not exist, skipping delete")
        return
    print(f"Deleting file: {file} - Size: {sizeof_fmt(file_stat['size'])}")
    with start_shell(dev) as ss:
        ss.run(f'cli -c "file delete {file}"')


def copy_file(dev: Device, file: str, date: str) -> None:
    """transfer a file from the device via SCP"""

    # Create directory on the desktop named after the host we're connecting to
    host_dir = os.path.expanduser(f"~/Desktop/{dev.hostname}")
    path = os.path.join(host_dir, date)
    os.makedirs(path, exist_ok=True)
    print(f"Destination directory: {path}")

    file_system = FS(dev)
    file_stat = file_system.stat(file)
    if file_stat is None or file_stat["size"] is None:
        print(f"Error: file {file} does not exist")
        return
    print(f"Copying file: {file} - Size: {sizeof_fmt(file_stat['size'])}")
    with SCP(dev, progress=True) as scp:
        scp.get(file, path)


def run_show_cmds(ss: StartShell, file: str, commands: Iterable[Command]) -> None:
    """Run a list of show commands, saving the first and appending the rest"""

    for index, command in enumerate(commands):
        if isinstance(command, tuple):
            cmd, timeout = command if len(command) == 2 else (command[0], None)
        else:
            cmd, timeout = command, None
        if not cmd:
            continue
        action = "save" if index == 0 else "append"
        cli_cmd = f'cli -c "{cmd} | {action} {file}"'
        if timeout is not None:
            ss.run(cli_cmd, timeout=timeout)
        else:
            ss.run(cli_cmd)


def collect_via_shell(
    dev: Device,
    date: str,
    label: str,
    description: str,
    commands: Sequence[Command],
    done_message: str = "Done",
) -> None:
    """Generic collector helper that handles remote file lifecycle"""

    file = f"/var/tmp/{date}_{dev.hostname}_{label}.txt"
    print(description)
    try:
        with start_shell(dev) as ss:
            run_show_cmds(ss, file, commands)
    finally:
        copy_file(dev, file, date)
        delete_file(dev, file)
        print(done_message)


# list of functions we'll call to generate and then collect the data
def collect_rsi(dev: Device, date: str, is_cluster: bool) -> None:
    """collect 'request support information'"""
    command = (
        "request support information all-members" if is_cluster else "request support information"
    )
    collect_via_shell(
        dev,
        date,
        "rsi",
        "Creating RSI...",
        [(command, 600)],
    )


def collect_logs(dev: Device, date: str) -> None:
    """collect logs"""
    # File to create on remote device
    file = f"/var/tmp/{date}_{dev.hostname}_varlog.tgz"

    # Compress /var/log/ to /var/tmp/pyez_varlog.tgz
    print("Compressing /var/log/*")
    file_system = FS(dev)
    file_system.tgz("/var/log/*", file)

    # Copy file to localhost
    copy_file(dev, file, date)

    # cleanup after ourselves
    delete_file(dev, file)

    print("Done")


def collect_chassis(dev: Device, date: str, is_cluster: bool) -> None:
    """collect chassis information"""
    commands: list[tuple[str, int | None]] = [("show chassis fpc pic-status", None)]
    if is_cluster:
        commands.extend(
            [
                ("show chassis cluster status", None),
                ("show chassis cluster interfaces", None),
                ("show chassis cluster statistics", None),
                ("show chassis cluster information", None),
                ("show chassis cluster ip-monitoring status", None),
            ]
        )
    collect_via_shell(
        dev,
        date,
        "chassis",
        "Collecting Chassis Information",
        commands,
        done_message="Done with chassis information",
    )


def collect_security_flow(dev: Device, date: str) -> None:
    """collect security flow information"""
    commands: list[tuple[str, int | None]] = [
        ("show security flow session summary", 120),
        ("show security flow cp-session summary", 120),
        ("show interface extensive", 120),
        ("show arp no-resolve", None),
    ]
    collect_via_shell(
        dev,
        date,
        "security_flows",
        "Collecting security flow information",
        commands,
    )


def get_ike_sa_indices(dev: Device) -> list[str]:
    """enumerate IKE security association indices via RPC"""
    try:
        data = dev.rpc.get_ike_security_associations_information()
        indices = [
            sa.findtext("ike-sa-index") for sa in data.findall(".//ike-security-associations")
        ]
        return [idx for idx in indices if idx]
    except RpcError as err:
        print(f"WARNING: could not enumerate IKE SAs: {err}")
        return []


def collect_ipsec_routed(dev: Device, date: str, is_cluster: bool) -> None:
    """collect ipsec routed tunnel information"""
    ike_indices = get_ike_sa_indices(dev)
    ike_summary = (
        "show security ike security-association all-members"
        if is_cluster
        else "show security ike security-association"
    )
    ipsec_summary = (
        "show security ipsec security-association all-members"
        if is_cluster
        else "show security ipsec security-association"
    )
    commands: list[tuple[str, int | None]] = [(ike_summary, 120)]
    commands.extend(
        (f"show security ike security-association index {idx} detail", 120) for idx in ike_indices
    )
    commands.append((ipsec_summary, 120))
    commands.extend(
        [
            ("show security ipsec statistics", None),
            ("show security ipsec next-hop-tunnels", None),
            ("show security flow session tunnel", 120),
            ("show route", 120),
            ("show security pki local-cert detail", None),
            ("show security pki ca-cert detail", None),
            ("show security pki crl detail", None),
        ]
    )
    collect_via_shell(
        dev,
        date,
        "ipsec_routed",
        "Collecting IPSec routed tunnel information",
        commands,
    )


def collect_ipsec_policy(dev: Device, date: str, is_cluster: bool) -> None:
    """collect ipsec policy tunnel information"""
    ike_indices = get_ike_sa_indices(dev)
    ike_summary = (
        "show security ike security-association all-members"
        if is_cluster
        else "show security ike security-association"
    )
    ipsec_summary = (
        "show security ipsec security-association all-members"
        if is_cluster
        else "show security ipsec security-association"
    )
    commands: list[tuple[str, int | None]] = [("show system licenses", None), (ike_summary, 120)]
    commands.extend(
        (f"show security ike security-association index {idx} detail", 120) for idx in ike_indices
    )
    commands.append((ipsec_summary, 120))
    commands.extend(
        [
            ("show security ipsec statistics", None),
            ("show security ipsec next-hop-tunnels", None),
            ("show security flow session tunnel", 120),
            ("show security pki local-cert detail", None),
            ("show security pki ca-cert detail", None),
            ("show security pki crl detail", None),
            ("show security policies detail", 120),
        ]
    )
    collect_via_shell(
        dev,
        date,
        "ipsec_policy",
        "Collecting IPSec policy tunnel information",
        commands,
    )


def collect_ipsec_dyn(dev: Device, date: str, is_cluster: bool) -> None:
    """collect dynamic ipsec information"""
    ike_indices = get_ike_sa_indices(dev)
    ike_summary = (
        "show security ike security-association all-members"
        if is_cluster
        else "show security ike security-association"
    )
    commands: list[tuple[str, int | None]] = [(ike_summary, 120)]
    commands.extend(
        (f"show security ike security-association index {idx} detail", 120) for idx in ike_indices
    )
    commands.extend(
        [
            ("show security ike active-peer", 120),
            ("show security ipsec security-association", 120),
            ("show security ipsec statistics", None),
            ("show security dynamic-vpn client version", None),
            ("show security dynamic-vpn users detail", 120),
            ("show system licenses", None),
        ]
    )
    collect_via_shell(
        dev,
        date,
        "ipsec_dyn",
        "Collecting IPSec dynamic VPN information",
        commands,
    )


def collect_high_cpu(dev: Device, date: str, is_srx: bool) -> None:
    """collect cpu statistics"""
    commands: list[tuple[str, int | None]] = [
        ("show chassis routing-engine", None),
        ("show system processes extensive", None),
        ("show system users", None),
        ("show system connections", None),
        ("show system statistics", None),
        ("show chassis forwarding", None),
    ]
    if is_srx:
        commands.extend(
            [
                ("show security monitor performance spu", None),
                ("show security monitor performance sess", None),
            ]
        )
    collect_via_shell(
        dev,
        date,
        "high_cpu",
        "Collecting high cpu information",
        commands,
    )


def collect_ospf(dev: Device, date: str) -> None:
    """collect ospf information"""
    commands: list[tuple[str, int | None]] = [
        ("show ospf overview", None),
        ("show ospf database extensive", None),
        ("show ospf detail", None),
        ("show ospf route", None),
        ("show ospf statistics", None),
        ("show ospf interface", None),
        ("show ospf log", None),
        ("show route protocol ospf", None),
    ]
    collect_via_shell(
        dev,
        date,
        "ospf",
        "Collecting OSPF information",
        commands,
    )


def collect_ospf3(dev: Device, date: str) -> None:
    """collect ospf3 information"""
    commands: list[tuple[str, int | None]] = [
        ("show ospf3 overview", None),
        ("show ospf3 database extensive", None),
        ("show ospf3 detail", None),
        ("show ospf3 route", None),
        ("show ospf3 statistics", None),
        ("show ospf3 interface", None),
        ("show ospf3 log", None),
        ("show route protocol ospf3", None),
    ]
    collect_via_shell(
        dev,
        date,
        "ospf3",
        "Collecting OSPF3 information",
        commands,
    )


def collect_bgp(dev: Device, date: str) -> None:
    """collect bgp information"""
    commands: list[tuple[str, int | None]] = [
        ("show bgp summary", None),
        ("show bgp neighbor", None),
        ("show route forwarding-table", None),
        ("show route resolution unresolved", None),
    ]
    collect_via_shell(
        dev,
        date,
        "bgp",
        "Collecting BGP information",
        commands,
    )


def collect_multicast(dev: Device, date: str) -> None:
    """collect multicast routing information"""
    commands: list[tuple[str, int | None]] = [
        ("show multicast router", None),
        ("show multicast statistics", None),
        ("show multicast sessions", None),
        ("show multicast usage", None),
        ("show multicast interface", None),
        ("show multicast next-hops", None),
        ("show multicast rpf summary", None),
        ("show interface extensive", 120),
        ("show igmp group detail", None),
        ("show igmp statistics", None),
        ("show igmp interface detail", None),
        ("show pim statistics", None),
        ("show pim neighbors", None),
        ("show pim rps detail", None),
        ("show pim join extensive", 120),
        ("show pim bootstrap", None),
        ("show msdp source-active", None),
        ("show msdp detail", None),
        ("show msdp statistics", None),
        ("show route", 120),
    ]
    collect_via_shell(
        dev,
        date,
        "multicast",
        "Collecting multicast information",
        commands,
    )


def collect_alg(dev: Device, date: str) -> None:
    """collect alg information"""
    commands: list[tuple[str, int | None]] = [
        ("show security alg status", None),
        ("show security resource-manager summary", None),
        ("show security resource-manager resource active", None),
        ("show security resource-manager group active", None),
        ("show security flow gate", 120),
    ]
    collect_via_shell(
        dev,
        date,
        "alg",
        "Collecting ALG information",
        commands,
    )


def collect_utm_av(dev: Device, date: str) -> None:
    """collect utm anti-virus information"""
    commands: list[tuple[str, int | None]] = [
        ("show system licenses", None),
        ("show security utm status", None),
        ("show security utm session", None),
        ("show security utm anti-virus status detail", None),
        ("show security utm anti-virus statistics", None),
        ("show chassis routing-engine", None),
        ("show system processes extensive", 120),
    ]
    collect_via_shell(
        dev,
        date,
        "utm_av",
        "Collecting UTM anti-virus information",
        commands,
    )


def collect_utm_as(dev: Device, date: str) -> None:
    """collect utm anti-spam information"""
    commands: list[tuple[str, int | None]] = [
        ("show system licenses", None),
        ("show security utm status", None),
        ("show security utm session", None),
        ("show security utm anti-spam status", None),
        ("show security utm anti-spam statistics", None),
        ("show chassis routing-engine", None),
        ("show system processes extensive", 120),
    ]
    collect_via_shell(
        dev,
        date,
        "utm_as",
        "Collecting UTM anti-spam information",
        commands,
    )


def collect_utm_web(dev: Device, date: str) -> None:
    """collect utm web-filtering information"""
    commands: list[tuple[str, int | None]] = [
        ("show system licenses", None),
        ("show security utm status", None),
        ("show security utm session", None),
        ("show security utm web-filtering status", None),
        ("show security utm web-filtering statistics", None),
        ("show chassis routing-engine", None),
        ("show system processes extensive", 120),
    ]
    collect_via_shell(
        dev,
        date,
        "utm_web",
        "Collecting UTM web-filtering information",
        commands,
    )


def collect_utm_content(dev: Device, date: str) -> None:
    """collect utm content-filtering information"""
    commands: list[tuple[str, int | None]] = [
        ("show system licenses", None),
        ("show security utm status", None),
        ("show security utm session", None),
        ("show security utm content-filtering statistics", None),
    ]
    collect_via_shell(
        dev,
        date,
        "utm_content",
        "Collecting UTM content-filtering information",
        commands,
    )


def collect_coredumps(dev: Device, date: str) -> None:
    """collect core dumps from the device"""

    print("Checking for core dumps")
    core_dumps = dev.rpc.get_system_core_dumps()
    file_count = core_dumps.findtext("directory/total-files")

    # enumerate core dump paths from the RPC output (the shell glob
    # "/var/crash/*" does not expand, so each file is transferred individually)
    paths = set()
    for output in core_dumps.xpath(".//output"):
        if output.text is None:
            continue
        for line in output.text.splitlines():
            tokens = line.split()
            if tokens and tokens[0].startswith("/") and "No such file" not in line:
                paths.add(tokens[0])

    if not paths:
        if file_count is not None and file_count.isdigit() and int(file_count) > 0:
            print("WARNING: core dumps present but their paths could not be enumerated")
        else:
            print("No core dumps to collect")
        return

    print(f"Found {len(paths)} core dump file(s)")
    for path in sorted(paths):
        copy_file(dev, path, date)


def configured_protocols(dev: Device) -> dict[str, bool]:
    """return protocol enablement flags (single RPC for <protocols>)"""

    xml_filter = "<configuration><protocols/></configuration>"
    data = dev.rpc.get_config(filter_xml=xml_filter, options={"format": "set"})
    config = etree.tostring(data, encoding="unicode")
    return {
        "bgp": " bgp " in config,
        "ospf": " ospf " in config,
        "ospf3": " ospf3 " in config,
        "multicast": any(proto in config for proto in (" pim ", " igmp ", " msdp ")),
    }


def configured_security(dev: Device) -> dict[str, bool]:
    """return security-feature enablement flags (single RPC for <security>)"""

    xml_filter = "<configuration><security/></configuration>"
    data = dev.rpc.get_config(filter_xml=xml_filter, options={"format": "set"})
    config = etree.tostring(data, encoding="unicode")
    return {
        "ipsec": any(tag in config for tag in (" ike ", " ipsec ")),
    }


# Method for human readable size-output
def sizeof_fmt(num: float, suffix: str = "B") -> str:
    """make size numbers human readable"""
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(usage="jtac_collector.py -d <hostname> -u <username>")
    parser.add_argument("-d", "--device", help="Enter a Juniper device (name or IP)")
    parser.add_argument(
        "-u",
        "--username",
        default="automation",
        help="Enter the username (default: automation)",
    )
    parser.add_argument("-k", "--ssh-key", help="Path to SSH private key for authentication")
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Collect everything (default is just RSI and logs)",
    )
    return parser


def run_collections(
    dev: Device,
    date: str,
    is_cluster: bool,
    is_srx: bool,
    collect_all: bool,
) -> None:
    collect_rsi(dev, date, is_cluster)
    time.sleep(SLEEP_LONG)
    collect_logs(dev, date)

    if not collect_all:
        return

    protocols = configured_protocols(dev)
    has_bgp = protocols["bgp"]
    has_ospf = protocols["ospf"]
    has_ospf3 = protocols["ospf3"]
    has_multicast = protocols["multicast"]
    has_ipsec = configured_security(dev)["ipsec"] if is_srx else False

    time.sleep(SLEEP_LONG)
    collect_chassis(dev, date, is_cluster)
    if is_srx:
        time.sleep(SLEEP_LONG)
        collect_security_flow(dev, date)
        time.sleep(SLEEP_LONG)
        if has_ipsec:
            time.sleep(SLEEP_SHORT)
            collect_ipsec_routed(dev, date, is_cluster)
            time.sleep(SLEEP_LONG)
            collect_ipsec_policy(dev, date, is_cluster)
            time.sleep(SLEEP_LONG)
            collect_ipsec_dyn(dev, date, is_cluster)

    time.sleep(SLEEP_LONG)
    collect_high_cpu(dev, date, is_srx)
    time.sleep(SLEEP_LONG)
    if has_bgp:
        time.sleep(SLEEP_SHORT)
        collect_bgp(dev, date)

    time.sleep(SLEEP_LONG)
    if has_ospf:
        time.sleep(SLEEP_SHORT)
        collect_ospf(dev, date)

    time.sleep(SLEEP_LONG)
    if has_ospf3:
        time.sleep(SLEEP_SHORT)
        collect_ospf3(dev, date)

    time.sleep(SLEEP_LONG)
    if has_multicast:
        time.sleep(SLEEP_SHORT)
        collect_multicast(dev, date)

    if is_srx:
        time.sleep(SLEEP_LONG)
        collect_alg(dev, date)
        time.sleep(SLEEP_LONG)
        collect_utm_av(dev, date)
        time.sleep(SLEEP_LONG)
        collect_utm_as(dev, date)
        time.sleep(SLEEP_LONG)
        collect_utm_web(dev, date)
        time.sleep(SLEEP_LONG)
        collect_utm_content(dev, date)

    time.sleep(SLEEP_LONG)
    collect_coredumps(dev, date)


def main() -> None:
    """main"""

    parser = build_parser()
    args = parser.parse_args()

    host = args.device or input("Device hostname: ")
    username = args.username

    date = datetime.datetime.now(tz=datetime.UTC).astimezone().strftime("%Y-%m-%d_%H-%M")

    connect_kwargs = {"host": host, "user": username}
    if args.ssh_key:
        connect_kwargs["ssh_private_key_file"] = args.ssh_key
    dev = cast(Device, Device(**connect_kwargs))
    try:
        dev.open()
    except ConnectError as err:
        print(f"ERROR: failed to connect to {host}: {err}")
        return
    dev.timeout = 120
    dev.banner_timeout = 60  # pyright: ignore[reportAttributeAccessIssue]

    try:
        print("Connected successfully...")

        if dev.facts["vc_mode"] == "Enabled":
            print("Working with a Virtual-Chassis cluster")
        if dev.facts["srx_cluster"]:
            print("Working with an SRX cluster")
        is_cluster = dev.facts["vc_mode"] == "Enabled" or dev.facts["srx_cluster"]

        is_srx = "SRX" in dev.facts["model"]
        if is_srx:
            print(f"Working with a {dev.facts['model']}")

        run_collections(dev, date, is_cluster, is_srx, args.all)
    finally:
        if dev.connected:
            try:
                dev.close()
            except (EOFError, OSError) as err:
                print(f"WARNING: connection close failed: {err}")
            else:
                print("Connection closed...")


if __name__ == "__main__":
    main()
