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
import datetime
import argparse
import os
from io import StringIO
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

    print("Connected successfully to {}".format(device))
    print("Pinging device {} from {}".format(target, routing_instance))

    ping_result = dev.rpc.ping(count=count,
                               host=target,
                               instance=routing_instance,
                               normalize=True)

    ping_result_str=etree.tostring(ping_result, encoding="unicode")

    f=StringIO(ping_result_str)
    context = etree.parse(f)
    root=context.getroot()
    for element in root.iter():
        print(f"{element.tag}={element.text}")
    # ping-results=None
    # target-host=1.1.1.1
    # target-ip=1.1.1.1
    # packet-size=56
    # probe-result=None
    # probe-index=1
    # probe-success=None
    # sequence-number=0
    # ip-address=1.1.1.1
    # time-to-live=59
    # response-size=64
    # rtt=24653
    # probe-results-summary=None
    # probes-sent=1
    # responses-received=1
    # packet-loss=0
    # rtt-minimum=24653
    # rtt-maximum=24653
    # rtt-average=24653
    # rtt-stddev=0
    # ping-success=None

    dev.close()
    print("Connection closed...")


if __name__ == "__main__":
    main()
