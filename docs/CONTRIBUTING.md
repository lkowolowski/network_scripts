## Documentation Workflow

This repo keeps one Markdown file per script under `docs/`. To add or update docs:

1. **Create/Edit `docs/<script>.md`:**
   - Sections: Overview, Capabilities, Usage, Requirements, Sample Output, Integrations (if any), CLI Reference.
   - Keep instructions concise; offload long examples to code blocks.
2. **Update the index:** add/remove entries in `docs/README.md` and the summary table in the root `README.md`.
3. **Regenerate CLI help snapshots:**
   ```bash
   python docs/update_cli_help.py
   ```
   This writes `docs/generated/*_help.md` so every script's `--help` stays in sync with documentation.
4. **Verify links:** ensure each per-script doc references its generated help file via `generated/<name>_help.md`.

### Adding a New Script

1. Place the script at the repo root (matching the existing pattern) and ensure it uses uv for dependencies.
2. Add a doc file under `docs/` plus an entry in `docs/README.md` and the main README table.
3. Run `python docs/update_cli_help.py` so the new help snapshot is tracked.
4. If the script exposes flags, add a "Sample Output" section showing expected behavior.
