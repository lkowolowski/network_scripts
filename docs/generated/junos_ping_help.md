## junos_ping.py

```
usage: junos_ping.py [-h] -d DEVICE -t TARGET [-c COUNT] [-i VRF]
                     [-u USERNAME] [-o {line,json}] [-v]

Execute a ping from a Junos device using NETCONF

options:
  -h, --help            show this help message and exit
  -d DEVICE, --device DEVICE
                        Juniper device (hostname or IP) to source the ping
                        from
  -t TARGET, --target TARGET
                        Target IP address to ping
  -c COUNT, --count COUNT
                        Number of pings to send (default: 1)
  -i VRF, --vrf VRF     VRF / routing-instance to use (default: default)
  -u USERNAME, --username USERNAME
                        Username to connect as (default: automation)
  -o {line,json}, --output-format {line,json}
                        Telegraf output format for stdout (default: line
                        protocol)
  -v, --verbose         Print human-readable connection logs to stderr
```
