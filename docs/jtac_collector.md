## `jtac_collector.py`

Turnkey workflow for gathering everything JTAC usually requests (RSI, logs, chassis data, protocol dumps) from a Junos device or cluster.

### Capabilities
- Establishes a NETCONF session and stretches timeouts for slow SRX/branch platforms.
- Detects Virtual Chassis and SRX clusters to run `request support information all-members` and cluster-specific `show chassis cluster ...` commands.
- Generates and downloads the following bundles to `~/Desktop/<device>`:
  - `*_rsi.txt` — `request support information` output.
  - `*_varlog.tgz` — archived `/var/log` contents.
  - `*_chassis.txt` — chassis details plus cluster status.
  - Optional security flow, OSPF, and OSPF3 captures when those features are configured.
- Cleans up `/var/tmp` artifacts after SCP transfers finish so the device stays tidy.

### Usage
```bash
./jtac_collector.py --device edge01.example.net --username automation
```

- If flags are omitted the script prompts interactively.
- Desktop output directories are named after the connected device.

### Sample Output
After a successful run you can expect a desktop folder such as `~/Desktop/srx01/` containing files like:

| File | Contents |
| --- | --- |
| `2025-05-12_15-00_srx01_rsi.txt` | `request support information` (all members when VC/SRX detected) |
| `2025-05-12_15-05_srx01_varlog.tgz` | Archived `/var/log` directory |
| `2025-05-12_15-10_srx01_chassis.txt` | `show chassis fpc/pic-status` plus cluster stats |
| `2025-05-12_15-15_srx01_security_flows.txt` | Security flow sessions (SRX only) |
| `2025-05-12_15-20_srx01_ospf.txt` | OSPF data if protocol present |
| `2025-05-12_15-25_srx01_ospf3.txt` | OSPFv3 data if protocol present |

### Requirements
- Python 3.12 via `uv run --script`.
- `junos-eznc`, `lxml`; automatically resolved by the script header.
- For Python 3.13+, install `telnetlib-313-and-up` until Juniper updates `junos-eznc`.

### Notes
- Sleep intervals between collection phases protect the device from consecutive heavy commands—avoid shortening them unless you fully control box load.
- Ensure NETCONF SSH rate limits are disabled or increased, otherwise the multi-minute RSI/log capture can be cut off mid-transfer.
- The script currently targets classic routing engines; adapt commands before using on non-Junos platforms.

### CLI Reference
Generated parser help: [docs/generated/jtac_collector_help.md](generated/jtac_collector_help.md)
