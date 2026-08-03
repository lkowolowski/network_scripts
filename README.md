# Network Scripts

Misc Juniper-related scripts designed to run via `uv run --script` so dependencies stay isolated and portable.

## Script Catalog

| Script                 | Summary                                                                                                                                                                                                                                                              | Documentation                                          |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| `jtac_collector.py`    | Builds JTAC-ready bundles (RSI, `/var/log`, and with `--all`: chassis, high-CPU, multicast, OSPF/OSPF3, security flow, IPSec, ALG, UTM, and core dumps — protocol/IPSec data collected only when configured) and stores them under `~/Desktop/<device>/<timestamp>`. | [docs/jtac_collector.md](docs/jtac_collector.md)       |
| `junos_ping.py`        | Executes device-sourced pings over NETCONF and emits Telegraf-friendly metrics (line protocol or JSON).                                                                                                                                                              | [docs/junos_ping.md](docs/junos_ping.md)               |
| `junos_print_facts.py` | Connects via NETCONF and prints `Device.facts` for quick inventory checks.                                                                                                                                                                                           | [docs/junos_print_facts.md](docs/junos_print_facts.md) |
| `junos_version.py`     | Selenium proof-of-concept for scraping Juniper's suggested releases page (currently a stub).                                                                                                                                                                         | [docs/junos_version.md](docs/junos_version.md)         |

## Troubleshooting

If you experience unexpected NETCONF disconnects or timeouts, verify the device is not enforcing aggressive limits:

```bash
system services netconf ssh rate-limit
```

Disabling or loosening that knob often prevents sessions from being killed mid-transfer.
