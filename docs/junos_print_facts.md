## `junos_print_facts.py`

Minimal helper that connects to a Junos device, prints `Device.facts`, and disconnects—ideal for quick inventory checks or scripting hand-offs.

### Capabilities
- Uses `jnpr.junos.Device` with elevated NETCONF timeouts for slow SRX branches.
- Pretty-prints the full `facts` dictionary (hostname, model, serial, personality, VC/SRX cluster flags, etc.).
- Leaves no files on the device and closes the NETCONF session cleanly.

### Usage
```bash
./junos_print_facts.py --device edge01.example.net --username automation
```

- Omitting flags triggers interactive prompts.
- Pipe the output into `jq`/`python -m json.tool` if you need machine parsing.

### Sample Output
```
Connected successfully...
{'hostname': 'edge01',
 'model': 'SRX345',
 'serialnumber': 'JN1234ABCD',
 'personality': 'SRX_BRANCH',
 'vc_mode': 'Enabled',
 'vc_master': True,
 'srx_cluster': False,
 ...}
Connection closed...
```

### Requirements
- Python 3.12 via `uv run --script`.
- `junos-eznc` dependency handled by uv.
- `telnetlib-313-and-up` required temporarily if you run under Python 3.13+.

### Notes
- This script intentionally avoids Telegraf/metrics integrations—use it ad‑hoc while developing inventory automations.
- Extend it by importing the module and reusing the `Device` session if you need richer data than `facts` exposes.

### CLI Reference
Generated parser help: [docs/generated/junos_print_facts_help.md](generated/junos_print_facts_help.md)
