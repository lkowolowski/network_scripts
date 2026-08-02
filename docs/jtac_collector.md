# `jtac_collector.py`

Turnkey workflow for gathering everything JTAC usually requests (RSI, logs, chassis data, protocol dumps) from a Junos device or cluster.

## Capabilities

- Establishes a NETCONF session and stretches timeouts for slow SRX/branch platforms.
- Detects Virtual Chassis and SRX clusters to run `request support information all-members` and cluster-specific `show chassis cluster ...` commands.
- Generates and downloads the following bundles to `~/Desktop/<device>`:
  - `*_rsi.txt` — `request support information` output.
  - `*_varlog.tgz` — archived `/var/log` contents.
  - With `--all`: `*_chassis.txt`, high-CPU stats, multicast, OSPF, OSPF3, security flow, ALG, and UTM captures.
  - BGP, IPSec, multicast, OSPF, and OSPF3 collectors run only when the feature is configured on the device.
  - Core dump files are copied individually (no shell glob) and left on the device.
- Cleans up `/var/tmp` artifacts after SCP transfers finish so the device stays tidy.

## Usage

```bash
./jtac_collector.py --device edge01.example.net --username automation
```

- If flags are omitted the script prompts interactively.
- Desktop output directories are named after the connected device.
- Add `--all` for the full capture (default is just RSI and logs):

```bash
./jtac_collector.py --device edge01.example.net --username automation --all
```

## Sample Output

After a successful run you can expect a desktop folder such as `~/Desktop/srx01/` containing files like:

| File | Contents |
| --- | --- |
| `2025-05-12_15-00_srx01_rsi.txt` | `request support information` (all members when VC/SRX detected) |
| `2025-05-12_15-05_srx01_varlog.tgz` | Archived `/var/log` directory |
| `2025-05-12_15-10_srx01_chassis.txt` | `show chassis fpc/pic-status` plus cluster stats |
| `2025-05-12_15-15_srx01_security_flows.txt` | Security flow sessions (SRX only, with `--all`) |
| `2025-05-12_15-20_srx01_high_cpu.txt` | Routing-engine/process CPU stats (with `--all`) |
| `2025-05-12_15-25_srx01_bgp.txt` | BGP summary/neighbors, forwarding table (with `--all`) |
| `2025-05-12_15-30_srx01_ipsec_routed.txt` | IPSec routed tunnels incl. per-SA IKE detail (SRX only, with `--all`) |
| `2025-05-12_15-35_srx01_ipsec_policy.txt` | IPSec policy tunnels, security policies (SRX only, with `--all`) |
| `2025-05-12_15-40_srx01_ipsec_dyn.txt` | IPSec dynamic-VPN, active IKE peers (SRX only, with `--all`) |
| `2025-05-12_15-45_srx01_ospf.txt` | OSPF data if protocol present |
| `2025-05-12_15-50_srx01_ospf3.txt` | OSPFv3 data if protocol present |
| `2025-05-12_15-55_srx01_multicast.txt` | Multicast/IGMP/PIM/MSDP data when those protocols are configured |
| `2025-05-12_16-00_srx01_alg.txt` | ALG status and resource-manager data (SRX only) |
| `2025-05-12_16-05_srx01_utm_av.txt` | UTM anti-virus data (SRX only) |
| `2025-05-12_16-10_srx01_utm_as.txt` | UTM anti-spam data (SRX only) |
| `2025-05-12_16-15_srx01_utm_web.txt` | UTM web-filtering data (SRX only) |
| `2025-05-12_16-20_srx01_utm_content.txt` | UTM content-filtering data (SRX only) |
| `2025-05-12_16-25_srx01_core_*.tgz` | Core dump files copied individually when present (left on device) |

## Requirements

- Python 3.12 via `uv run --script`.
- `junos-eznc`, `lxml`; automatically resolved by the script header.
- For Python 3.13+, install `telnetlib-313-and-up` until Juniper updates `junos-eznc`.

## Notes

- Sleep intervals between collection phases protect the device from consecutive heavy commands—avoid shortening them unless you fully control box load.
- Ensure NETCONF SSH rate limits are disabled or increased, otherwise the multi-minute RSI/log capture can be cut off mid-transfer.
- The script currently targets classic routing engines; adapt commands before using on non-Junos platforms.

## CLI Reference

Generated parser help: [docs/generated/jtac_collector_help.md](generated/jtac_collector_help.md)
