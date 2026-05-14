## `junos_ping.py`

NETCONF-powered, device-sourced ping testing for Junos gear.

### Capabilities
- Launch ICMP probes from any reachable Junos device without interactive SSH.
- Choose target, count, VRF, username, and output format (`line` or `json`).
- Validates arguments (`count > 0`) and stringifies RPC inputs to satisfy `jnpr.junos` expectations.
- Performs a local `ping -qc 1 <device>` reachability check before opening NETCONF.
- Uses a context-managed `Device` session so connections always close, even on RPC errors.
- Emits a single metrics record per run with packet + RTT stats normalized to seconds, plus fallback `success=0` metrics when failures occur.

### Usage
```bash
# Default line-protocol metrics, VRF "default"
./junos_ping.py --device srx01 --target 1.1.1.1 --count 3

# Specific VRF, JSON metrics, with human logs on stderr
./junos_ping.py --device srx01 --target 1.1.1.1 --vrf mgmt \
  --output-format json --verbose
```

### Telegraf Integration
`junos_ping.py` is optimized for `inputs.exec` so Prometheus can scrape metrics via Telegraf.

**Line Protocol (default)**
```toml
[[inputs.exec]]
  commands = ["/path/to/junos_ping.py --device srx01 --target 1.1.1.1"]
  timeout = "10s"
  data_format = "influx"

[[outputs.prometheus_client]]
  listen = ":9273"
```

Each run emits one line like:
```
junos_ping,device=srx01,target=1.1.1.1,vrf=default packets_sent=3i,packets_received=3i,success=1i,rtt_avg_seconds=0.021234
```

**JSON Output**
```toml
[[inputs.exec]]
  commands = ["/path/to/junos_ping.py --device srx01 --target 1.1.1.1 --output-format json"]
  timeout = "10s"
  data_format = "json_v2"
  [[inputs.exec.json_v2.object]]
    measurement_name = "measurement"
    tag_keys = ["tags.device", "tags.target", "tags.vrf"]
    field_keys = [
      "fields.packets_sent",
      "fields.packets_received",
      "fields.packet_loss",
      "fields.success",
      "fields.rtt_avg_seconds",
    ]
```

The script emits fallback metrics with `success=0` and `error="local_ping_failed"` / `error="no_responses"` when connectivity breaks, so alerting can key off failures.

### Sample Metrics
```
# Successful probe
junos_ping,device=srx01,target=1.1.1.1,vrf=default packets_sent=1i,packets_received=1i,success=1i,packet_loss=0i,rtt_avg_seconds=0.021

# Failed probe
junos_ping,device=srx01,target=10.10.10.1,vrf=default packets_sent=1i,packets_received=0i,success=0i,packet_loss=100i,error="no_responses"
```

### Requirements
- Python 3.12 managed by [uv](https://docs.astral.sh/uv/).
- `junos-eznc` and `lxml` (pulled automatically via uv).
- For Python 3.13+, manually install `telnetlib-313-and-up` until Juniper updates `junos-eznc`.

### Operational Notes
- If the script exits early with `ERROR: Unable to reach <device> via system ping`, fix local routing/DNS before retrying.
- NETCONF sessions can still hit SRX rate limits; disable `system services netconf ssh rate-limit` if drops persist.
- RTT values are reported in seconds (converted from Junos microseconds) without additional smoothing.

### CLI Reference
Generated parser help: [docs/generated/junos_ping_help.md](generated/junos_ping_help.md)
