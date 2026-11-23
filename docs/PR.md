# feat: hot-reload flows from LANGFLOW_LOAD_FLOWS_PATH

**Base branch:** `release-1.14.0` (per CONTRIBUTING.md, PRs target the active release branch, not `main`)
**Head branch:** `ava-l3nore:feat/watch-load-flows-path`

Fixes #11918

## Problem

`LANGFLOW_LOAD_FLOWS_PATH` is read once, at startup. A changed or added flow file has no effect until Langflow restarts. For teams that deploy flows from git, for example to a PVC-mounted directory kept in sync by GitOps, every flow change needs a `kubectl rollout restart`.

## What this changes

Adds an opt-in setting, `LANGFLOW_WATCH_FLOWS_PATH` (default `false`). When it is `true`, a background task checks the directory every `LANGFLOW_FS_FLOWS_POLLING_INTERVAL` ms (existing setting, default 10000) and applies new and changed `*.json` files through the existing `upsert_flow_from_file()`, using the same owner and the same `LOAD_FLOWS_*` rules as startup loading.

- **One writer.** Each pass takes the `load-flows-path-watch` row of the existing `trigger_lease` table, so with several workers or replicas only one process writes. This works on SQLite and PostgreSQL.
- **One-way.** A deleted file leaves its flow in place and logs one warning. Nothing is written back to disk.
- **Files win, with a warning.** If a flow was edited in the UI since its file was last applied, the next change to the file overwrites it and logs a warning naming the flow. Edits are detected with a SHA-256 fingerprint of the flow's name, description, and data, not with `updated_at`, which is stored without a time zone and written in both local time and UTC.
- **Safe failures.** Invalid JSON is skipped and retried when the file changes again. A missing directory or a missing `LANGFLOW_LOAD_FLOWS_PATH` logs a warning, and the watch doesn't start.
- **Migration-safe.** Passes run under `async_writing(name="flow_watch")`, like `sync_flows_from_fs`.

| File | Change |
|---|---|
| `src/lfx/src/lfx/services/settings/groups/components.py` | New `watch_flows_path` setting |
| `src/backend/base/langflow/initial_setup/setup.py` | `watch_flows_from_directory()` and helpers |
| `src/backend/base/langflow/main.py` | Start the task in the lifespan when enabled; cancel it on shutdown |
| `src/backend/tests/unit/initial_setup/test_watch_flows_from_directory.py` | 15 unit tests |
| `src/backend/tests/unit/initial_setup/test_watch_flows_system.py` | 3 system tests through the API |
| `docs/features/watch-load-flows-path.md` | Feature note |
| `docs/docs/Develop/environment-variables.mdx` | Documents `LANGFLOW_WATCH_FLOWS_PATH` |

## How to test

Automated:

```bash
uv run pytest src/backend/tests/unit/initial_setup/test_watch_flows_from_directory.py src/backend/tests/unit/initial_setup/test_watch_flows_system.py
```

Manually:

1. Put a flow JSON file in a directory, for example `~/demo-flows/demo.json`.
2. Start Langflow with `LANGFLOW_LOAD_FLOWS_PATH=~/demo-flows LANGFLOW_WATCH_FLOWS_PATH=true LANGFLOW_FS_FLOWS_POLLING_INTERVAL=2000 make backend`.
3. Change the flow's `name` or `description` in the file and save it. Within a few seconds, refresh the UI. The change is there with no restart.
4. Add a second file. It appears as a new flow.
5. Delete a file. Its flow stays, and the log shows a warning.
6. Without `LANGFLOW_WATCH_FLOWS_PATH`, step 3 has no effect until restart, which is the current behavior.

## Test results

| Suite | Result |
|---|---|
| New unit tests (`test_watch_flows_from_directory.py`) | 15 passed |
| New system tests (`test_watch_flows_system.py`) | 3 passed |
| Existing loader tests (`test_flow_loader_owner.py`, `test_upsert_flow_from_file.py`, `test_initial_setup.py`) | 71 passed |
| `ruff check` on changed files | All checks passed |

## Deliberately left out

- **Deleting flows when files are removed.** Deletion can't be undone, and a bad CI run that empties the directory would wipe flows. This could be a separate opt-in later.
- **Writing UI edits back to files.** Files are the source of truth.
- **An in-app notice that a flow is file-managed.** That's frontend work. This PR logs a warning instead.
- **Turning it on by default.** It would change behavior for existing deployments. It could be flipped in a later release.

## Risks

- **Lease takeover.** The record of applied files is kept in memory. If the lease moves to another process, that process may reapply files and overwrite a UI edit without the warning. Storing fingerprints in the database would fix this. I left it out to keep the change small.
- **Coupled interval.** Reusing `fs_flows_polling_interval` means one setting tunes both the `fs_path` sync and this watch.
- **Default off.** Nothing changes for anyone who doesn't set the variable.

## Questions for the reviewer

1. Is reusing `langflow.services.triggers.leases` acceptable here, or would you prefer the lease helpers moved to a shared module first?
2. Is a log warning enough for the UI-edit overwrite for now, or should the watch skip edited flows instead?
3. Would you want a separate interval setting instead of reusing `LANGFLOW_FS_FLOWS_POLLING_INTERVAL`?

🤖 Generated with [Claude Code](https://claude.com/claude-code)
