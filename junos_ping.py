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
import time
import datetime
import argparse
import os
from io import StringIO
from pprint import pprint
from lxml import etree
from jnpr.junos import Device
from jnpr.junos.exception import (
    ConnectAuthError,
    ConnectRefusedError,
    ConnectTimeoutError,
    ConnectError,
)

def main():
    """main"""

    parser = argparse.ArgumentParser(usage='junos_ping.py -d <hostname> -r <routing-instance> -t <target>')
    parser.add_argument('-d', '--device', help='Enter a Juniper device (name or IP) to ping from')
    parser.add_argument('-c', '--count', help='Enter the number of pnigs to send')
    parser.add_argument('-i', '--routing_instance', help='Enter the routing-instance')
    parser.add_argument('-t', '--target', help='Enter the target IP to ping')
    parser.add_argument('-u', '--username', help='Username to connect as')
    args = parser.parse_args()

    if not args.device:
        device = input('Junos device to ping from')
    else:
        device = args.device

    if not args.target:
        target = input('Target to ping')
    else:
        target = args.target

    if args.count is None:
        count="1"
    else:
        count=args.count

    if args.routing_instance is None:
        routing_instance="default"
    else:
        routing_instance=args.routing_instance

    if args.username is None:
        username="automation"
    else:
        username=args.username

    # Get timestamp for our output
    timestamp = time.time()

    # connect to the device with IP-address, login user and passwort
    dev = Device(host=device, user=username,
                 gather_facts=False)

    # open a connection to the device and start a NETCONF session
    response = os.system("ping -qc 1 " + device + ">/dev/null")
    if response == 0:
        try:
            dev.open()
        except ConnectAuthError:
            print("ERROR: Authentication failed.")
            return
        except ConnectRefusedError:
            print("ERROR: Connection refused.")
            return
        except ConnectTimeoutError:
            print("ERROR: Connection timed oud.")
            return
        except ConnectError:
            print("ERROR: Connection failed.")
            return

    # needed for file compression on srx340 because they are slow
    dev.timeout=120
    dev.banner_timeout=60

    print(f"Connected successfully to {device}")
    print(f"Pinging device {target} from {routing_instance}")

    ping_result = dev.rpc.ping(count=count,
                               host=target,
                               instance=routing_instance,
                               normalize=True)

    ping_result_str=etree.tostring(ping_result, encoding="unicode")


    f=StringIO(ping_result_str)
    context = etree.parse(f)
    root=context.getroot()

    # Useful for seeing what our xml tree looks like
    #def prettyprint(element, **kwargs):
    #    xml = etree.tostring(element, pretty_print=True, **kwargs)
    #    print(xml.decode(), end='')

    # printing out the xml tree
    # prettyprint(root)

    # want to have a line for each of:
    # rtt-minimum, rtt-maximum, rtt-average, rtt-stddev, packet-loss
    # It should look something like this:
    # latency,platform=junos,source=device,destination=target,routing_instance=instance rtt-minimum=value <timestamp>
    # latency,platform=junos,source=device,destination=target,routing_instance=instance rtt-maximum=value <timestamp>
    # latency,platform=junos,source=device,destination=target,routing_instance=instance rtt-average=value <timestamp>
    # latency,platform=junos,source=device,destination=target,routing_instance=instance rtt-stddev=value <timestamp>
    # latency,platform=junos,source=device,destination=target,routing_instance=instance packet-loss=value <timestamp>
    #
    rtt_min=root.find(".//rtt-minimum").text
    rtt_max=root.find(".//rtt-maximum").text
    rtt_avg=root.find(".//rtt-average").text
    rtt_stddev=root.find(".//rtt-stddev").text
    packet_loss=root.find(".//packet-loss").text

    print(f"latency,platform=junos,source={device},destination={target},instance={routing_instance},rtt-minimum={rtt_min} {timestamp:.0f}")
    print(f"latency,platform=junos,source={device},destination={target},instance={routing_instance},rtt-maximum={rtt_max} {timestamp:.0f}")
    print(f"latency,platform=junos,source={device},destination={target},instance={routing_instance},rtt-average={rtt_avg} {timestamp:.0f}")
    print(f"latency,platform=junos,source={device},destination={target},instance={routing_instance},rtt-stddev={rtt_stddev} {timestamp:.0f}")
    print(f"latency,platform=junos,source={device},destination={target},instance={routing_instance},packet-loss={packet_loss} {timestamp:.0f}")

    dev.close()
    print("Connection closed...")


if __name__ == "__main__":
    main()
