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
import os
import time
import datetime
import argparse
from jnpr.junos.utils.start_shell import StartShell
from jnpr.junos import Device
from jnpr.junos.utils.scp import SCP
from jnpr.junos.utils.fs import FS

def delete_file(dev,file):
    """delete a file"""
    ss = StartShell(dev)
    ss.open()
    # Get file system information
    file_system = FS(dev)
    file_stat = file_system.stat(file)
    print("Deleting file: "+file+" - Size: "+(str(sizeof_fmt(file_stat['size']))))
    ss.run('cli -c "file delete "'+file)
    ss.close()

def copy_file(dev,file):
    """Transfering files via SCP"""

    # Create directory on the desktop named after the host we're connecting to
    path=os.path.expanduser("~/Desktop/"+dev.hostname)
    if not os.path.exists(path):
        os.mkdir(path)
        print("Created destination directory: "+path)
    else:
        print("Destination directory already exists")

    # Get file system information
    file_system = FS(dev)
    file_stat = file_system.stat(file)
    # Get file
    if file_stat['size'] is not None:
        print("Copying file: "+file+" - Size: "+(str(sizeof_fmt(file_stat['size']))))
        with SCP(dev, progress=True) as scp:
            scp.get(file, path)
    else:
        print("Error: file "+file+" does not exist")

def collect_coredumps(dev):
    """collect coredumps"""
    core_dumps = dev.rpc.get_system_core_dumps()
    file_count = core_dumps.findtext('directory/total-files')
    if file_count is not None:
        with SCP(dev, progress=True) as scp:
            scp.get("/var/crash/*")
    else:
        print("No core dumps to collect")

# list of functions we'll call to generate and then collect the data
def collect_rsi(dev):
    """collect 'request support information'"""
    # File to create on remote device
    file = "/var/tmp/"+date+"_"+dev.hostname+"_rsi.txt"

    print("Creating RSI...")

    # If we have an error here, the file won't be created. This will cascade to copy
    # and will give an error about being unable to iterate None type
    ss = StartShell(dev)
    ss.open()
    ss.run('cli -c "request support information | save "'+file)
    ss.close()

    # Copy file to localhost
    copy_file(dev,file)

    # cleanup after ourselves
    delete_file(dev,file)

    print("Done")

def collect_logs(dev):
    """collect logs"""
    # File to create on remote device
    file = "/var/tmp/"+date+"_"+dev.hostname+"_varlog.tgz"


    # Compress /var/log/ to /var/tmp/pyez_varlog.tgz
    print("Compressing /var/log/*")
    file_system = FS(dev)
    file_system.tgz("/var/log/*",file)

    # Copy file to localhost
    copy_file(dev,file)

    # cleanup after ourselves
    delete_file(dev,file)

    print("Done")

# Method for human readable size-output
def sizeof_fmt(num, suffix='B'):
    """make size numbers human readable"""
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

# Get actuall date/time
now = datetime.datetime.now()
date = now.strftime("%Y-%m-%d_%H-%M")

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
        username = "automation"
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
    # Make sure we sleep a little after each collection so we don't tire the
    # device out to much and lose our connection
    collect_rsi(dev)
    time.sleep(30)
    collect_logs(dev)

    dev.close()
    print("Connection closed...")


main()
