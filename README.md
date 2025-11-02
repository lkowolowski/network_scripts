Misc Juniper related scripts.

These all leverage uv for dependency management. Should be portable anywhere you can
run uv.

## **JTAC collection**

This will collect information for submitting a JTAC case

## **Junos ping**

This will ping a destination from a specified junos device

## **Troubleshooting**

If you have problems with odd timeouts, look for

```bash
system services netconf ssh rate-limit
```

It may be killing connections before the script has finished.
