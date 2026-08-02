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

from jnpr.junos import Device
from jnpr.junos.exception import ConnectError
from jnpr.junos.utils.fs import FS
from jnpr.junos.utils.scp import SCP
from jnpr.junos.utils.start_shell import StartShell
from lxml import etree


def delete_file(dev, file):
    """delete a file"""
    file_system = FS(dev)
    file_stat = file_system.stat(file)
    if file_stat is None or file_stat["size"] is None:
        print(f"File {file} does not exist, skipping delete")
        return
    print(f"Deleting file: {file} - Size: {sizeof_fmt(file_stat['size'])}")
    with StartShell(dev) as ss:
        ss.run(f'cli -c "file delete {file}"')


def copy_file(dev, file):
    """transfer a file from the device via SCP"""

    # Create directory on the desktop named after the host we're connecting to
    path = os.path.expanduser(f"~/Desktop/{dev.hostname}")
    if not os.path.exists(path):
        os.mkdir(path)
        print(f"Created destination directory: {path}")
    else:
        print("Destination directory already exists")

    file_system = FS(dev)
    file_stat = file_system.stat(file)
    if file_stat is None or file_stat["size"] is None:
        print(f"Error: file {file} does not exist")
        return
    print(f"Copying file: {file} - Size: {sizeof_fmt(file_stat['size'])}")
    with SCP(dev, progress=True) as scp:
        scp.get(file, path)


# list of functions we'll call to generate and then collect the data
def collect_rsi(dev, date, is_cluster):
    """collect 'request support information'"""
    # File to create on remote device
    file = f"/var/tmp/{date}_{dev.hostname}_rsi.txt"

    print("Creating RSI...")

    # If the RSI command fails, the file won't be created; copy_file handles the
    # missing file gracefully and skips the transfer.
    # RSI can take minutes on busy boxes; give the shell run a generous timeout.
    with StartShell(dev) as ss:
        # find a way to collect this from all members in a cluster
        if is_cluster:
            ss.run(f'cli -c "request support information all-members | save {file}"', timeout=600)
        else:
            ss.run(f'cli -c "request support information | save {file}"', timeout=600)

    # Copy file to localhost
    copy_file(dev, file)

    # cleanup after ourselves
    delete_file(dev, file)

    print("Done")


def collect_logs(dev, date):
    """collect logs"""
    # File to create on remote device
    file = f"/var/tmp/{date}_{dev.hostname}_varlog.tgz"

    # Compress /var/log/ to /var/tmp/pyez_varlog.tgz
    print("Compressing /var/log/*")
    file_system = FS(dev)
    file_system.tgz("/var/log/*", file)

    # Copy file to localhost
    copy_file(dev, file)

    # cleanup after ourselves
    delete_file(dev, file)

    print("Done")


def collect_chassis(dev, date, is_cluster):
    """collect chassis information"""
    # file to create on remote device
    file = f"/var/tmp/{date}_{dev.hostname}_chassis.txt"

    print("Collecting Chassis Information")
    with StartShell(dev) as ss:
        ss.run(f'cli -c "show chassis fpc pic-status | save {file}"')
        if is_cluster:
            # collect all the bits that are cluster specific
            ss.run(f'cli -c "show chassis cluster status | append {file}"')
            ss.run(f'cli -c "show chassis cluster interfaces | append {file}"')
            ss.run(f'cli -c "show chassis cluster statistics | append {file}"')
            ss.run(f'cli -c "show chassis cluster information | append {file}"')
            ss.run(f'cli -c "show chassis cluster ip-monitoring status | append {file}"')

    # Copy file to localhost
    copy_file(dev, file)

    # Cleanup after ourselves
    delete_file(dev, file)

    print("Done with chassis information")


def collect_security_flow(dev, date):
    """collect security flow information"""
    # file to create on remote device
    file = f"/var/tmp/{date}_{dev.hostname}_security_flows.txt"

    print("Collecting security flow information")
    with StartShell(dev) as ss:
        ss.run(f'cli -c "show security flow session summary | save {file}"')
        ss.run(f'cli -c "show security flow cp-session summary | append {file}"')
        ss.run(f'cli -c "show interface extensive | append {file}"')
        ss.run(f'cli -c "show arp no-resolve | append {file}"')

    # copy file to localhost
    copy_file(dev, file)

    # cleanup after ourselves
    delete_file(dev, file)

    print("Done")


def collect_high_cpu(dev, date, is_srx):
    """collect cpu statistics"""
    # File to create on remote device
    file = f"/var/tmp/{date}_{dev.hostname}_high_cpu.txt"

    print("Collecting high cpu information")
    with StartShell(dev) as ss:
        ss.run(f'cli -c "show chassis routing-engine | save {file}"')
        ss.run(f'cli -c "show system processes extensive | append {file}"')
        ss.run(f'cli -c "show system users | append {file}"')
        ss.run(f'cli -c "show system connections | append {file}"')
        ss.run(f'cli -c "show system statistics | append {file}"')
        ss.run(f'cli -c "show chassis forwarding | append {file}"')
        if is_srx:
            ss.run(f'cli -c "show security monitor performance spu | append {file}"')
            ss.run(f'cli -c "show security monitor performance sess | append {file}"')

    # Copy file to localhost
    copy_file(dev, file)

    # Cleanup after ourselves
    delete_file(dev, file)

    print("Done")


def collect_ospf(dev, date):
    """collect ospf information"""

    # file to create on remote device
    file = f"/var/tmp/{date}_{dev.hostname}_ospf.txt"

    print("Collecting OSPF information")
    with StartShell(dev) as ss:
        ss.run(f'cli -c "show ospf overview | save {file}"')
        ss.run(f'cli -c "show ospf database extensive | append {file}"')
        ss.run(f'cli -c "show ospf detail | append {file}"')
        ss.run(f'cli -c "show ospf route | append {file}"')
        ss.run(f'cli -c "show ospf statistics | append {file}"')
        ss.run(f'cli -c "show ospf interface | append {file}"')
        ss.run(f'cli -c "show ospf log | append {file}"')
        ss.run(f'cli -c "show route protocol ospf | append {file}"')

    # copy file to localhost
    copy_file(dev, file)

    # cleanup after ourselves
    delete_file(dev, file)

    print("Done")


def collect_ospf3(dev, date):
    """collect ospf3 information"""

    # file to create on remote device
    file = f"/var/tmp/{date}_{dev.hostname}_ospf3.txt"

    print("Collecting OSPF3 information")
    with StartShell(dev) as ss:
        ss.run(f'cli -c "show ospf3 overview | save {file}"')
        ss.run(f'cli -c "show ospf3 database extensive | append {file}"')
        ss.run(f'cli -c "show ospf3 detail | append {file}"')
        ss.run(f'cli -c "show ospf3 route | append {file}"')
        ss.run(f'cli -c "show ospf3 statistics | append {file}"')
        ss.run(f'cli -c "show ospf3 interface | append {file}"')
        ss.run(f'cli -c "show ospf3 log | append {file}"')
        ss.run(f'cli -c "show route protocol ospf3 | append {file}"')

    # copy file to localhost
    copy_file(dev, file)

    # cleanup after ourselves
    delete_file(dev, file)

    print("Done")


def collect_bgp(dev, date):
    """collect bgp information"""
    # File to create on remote device
    file = f"/var/tmp/{date}_{dev.hostname}_bgp.txt"

    print("Collecting BGP information")
    with StartShell(dev) as ss:
        ss.run(f'cli -c "show bgp summary | save {file}"')
        ss.run(f'cli -c "show bgp neighbor | append {file}"')
        ss.run(f'cli -c "show route forwarding-table | append {file}"')
        ss.run(f'cli -c "show route resolution unresolved | append {file}"')

    # Copy file to localhost
    copy_file(dev, file)

    # Cleanup after ourselves
    delete_file(dev, file)

    print("Done")


def check_ospf(dev):
    """check if the device config has ospf"""

    xml_filter = "<configuration><protocols/></configuration>"
    data = dev.rpc.get_config(filter_xml=xml_filter, options={"format": "set"})
    return bool(" ospf " in etree.tostring(data, encoding="unicode"))


def check_ospf3(dev):
    """check if the device config has ospf3"""

    xml_filter = "<configuration><protocols/></configuration>"
    data = dev.rpc.get_config(filter_xml=xml_filter, options={"format": "set"})
    return bool(" ospf3 " in etree.tostring(data, encoding="unicode"))


# Method for human readable size-output
def sizeof_fmt(num, suffix="B"):
    """make size numbers human readable"""
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


def main():
    """main"""

    # cli arguments
    parser = argparse.ArgumentParser(usage="jtac_collector.py -d <hostname> -u <username>")
    parser.add_argument("-d", "--device", help="Enter a Juniper device (name or IP)")
    parser.add_argument("-u", "--username", help="Enter the username")
    parser.add_argument("-k", "--ssh-key", help="Path to SSH private key for authentication")
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Collect everything (default is just RSI and logs)",
    )
    args = parser.parse_args()

    if not args.device:
        host = input("Device hostname")
    else:
        host = args.device

    if not args.username:
        username = "automation"
    else:
        username = args.username

    date = datetime.datetime.now(tz=datetime.UTC).astimezone().strftime("%Y-%m-%d_%H-%M")

    # connect to the device with IP-address, login user and passwort
    connect_kwargs = {"host": host, "user": username}
    if args.ssh_key:
        connect_kwargs["ssh_private_key_file"] = args.ssh_key
    dev = Device(**connect_kwargs)
    try:
        dev.open()
    except ConnectError as err:
        print(f"ERROR: failed to connect to {host}: {err}")
        return
    # needed for file compression on srx340 because they are slow
    dev.timeout = 120
    dev.banner_timeout = 60  # pyright: ignore[reportAttributeAccessIssue]

    try:
        print("Connected successfully...")

        # define some bits based on facts we collected
        if dev.facts["vc_mode"] == "Enabled":
            print("Working with a Virtual-Chassis cluster")
        if dev.facts["srx_cluster"]:
            print("Working with an SRX cluster")
        is_cluster = dev.facts["vc_mode"] == "Enabled" or dev.facts["srx_cluster"]

        if "SRX" in dev.facts["model"]:
            print(f"Working with a {dev.facts['model']}")
            is_srx = True
        else:
            is_srx = False

        # Collect all our bits
        # Make sure we sleep a little after each collection so we don't tire the
        # device out to much and lose our connection
        collect_rsi(dev, date, is_cluster)
        time.sleep(30)
        collect_logs(dev, date)

        if args.all:
            time.sleep(30)
            collect_chassis(dev, date, is_cluster)
            if is_srx:
                time.sleep(30)
                collect_security_flow(dev, date)
            time.sleep(30)
            collect_high_cpu(dev, date, is_srx)
            time.sleep(30)
            collect_bgp(dev, date)

            time.sleep(30)
            running_ospf = check_ospf(dev)
            if running_ospf:
                time.sleep(10)
                collect_ospf(dev, date)

            time.sleep(30)
            running_ospf3 = check_ospf3(dev)
            if running_ospf3:
                time.sleep(10)
                collect_ospf3(dev, date)
    finally:
        if dev.connected:
            dev.close()
            print("Connection closed...")


if __name__ == "__main__":
    main()
