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
from pprint import pprint
from jnpr.junos.utils.start_shell import StartShell
from jnpr.junos import Device
from jnpr.junos.utils.scp import SCP
from jnpr.junos.utils.fs import FS

def main():
    """main"""
    parser = argparse.ArgumentParser(usage='jtac_collector.py -d <hostname> -u <username>')
    parser.add_argument('-d', '--device', help='Enter a Juniper device (name or IP)')
    parser.add_argument('-u', '--username', help='Enter the username')
    args = parser.parse_args()

    if not args.device:
        host = input('Device hostname')
    else:
        host = args.device

    if not args.username:
        username = input('Device username')
    else:
        username = args.username

    # connect to the device with IP-address, login user and passwort
    dev = Device(host=host, user=username)
    dev.open()
    # needed for file compression on srx340 because they are slow
    dev.timeout=120
    dev.banner_timeout=60

    print("Connected successfully...")

    # Collect all our bits
    pprint(dev.facts)

    #print ("Model: "+dev.facts['model'])

    dev.close()
    print("Connection closed...")


main()
