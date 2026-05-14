## `junos_version.py`

Experimental Selenium script intended to scrape Juniper's "Suggested Releases" portal.

### Current Behavior
- Opens a ChromeDriver session, navigates to `python.org` (placeholder), prints the page title and URL, then exits.
- Hard-codes the ChromeDriver path (`/opt/homebrew/bin/chromedriver`).

### Usage
```bash
./junos_version.py
```

### Sample Output
```
Python.org
https://www.python.org/
```

### Requirements
- Python 3.12 (uv-managed) with `selenium` and `pytest` dependencies per script header.
- Chrome + ChromeDriver installed locally; update the path in the script if needed.

### Next Steps / Recommendations
- Point the driver at Juniper's support portal (`junos_versions_url` constant already defined) and add authentication if required.
- Replace deprecated Selenium APIs with `driver.find_element(By.NAME, ...)` etc.
- Emit structured output (JSON/CSV) so downstream tooling can diff recommended releases.
- Consider running `seleniumbase` or headless Chrome inside CI if you plan to automate checks.

### CLI Reference
Generated parser help: [docs/generated/junos_version_help.md](generated/junos_version_help.md)
