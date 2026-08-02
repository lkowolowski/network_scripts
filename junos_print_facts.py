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

from jnpr.junos import Device


def main():
    """main"""
    parser = argparse.ArgumentParser(usage="junos_print_facts.py -d <hostname> -u <username>")
    parser.add_argument("-d", "--device", help="Enter a Juniper device (name or IP)")
    parser.add_argument("-u", "--username", help="Enter the username")
    parser.add_argument("-k", "--ssh-key", help="Path to SSH private key for authentication")
    args = parser.parse_args()

    if not args.device:
        host = input("Device hostname")
    else:
        host = args.device

    if not args.username:
        username = "automation"
    else:
        username = args.username

    # connect to the device with IP-address, login user and passwort
    connect_kwargs = {"host": host, "user": username}
    if args.ssh_key:
        connect_kwargs["ssh_private_key_file"] = args.ssh_key
    dev = Device(**connect_kwargs)
    dev.open()
    # needed for file compression on srx340 because they are slow
    dev.timeout = 120
    dev.banner_timeout = 60  # pyright: ignore[reportAttributeAccessIssue]

    print("Connected successfully...")

    # Collect all our bits
    pprint(dev.facts)

    # print ("Model: "+dev.facts['model'])

    dev.close()
    print("Connection closed...")


if __name__ == "__main__":
    main()
