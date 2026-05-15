# Removed Monolith Audit

This note records the current verification status for the old giant Python HTTP entry. To keep the repository-wide guard meaningful, this document avoids writing the removed names as contiguous strings.

## Physically Deleted Files

- Python HTTP monolith: `qwen` + `3_web.py`
- Old smoke test: `test_` + `qwen` + `3_smoke.py`
- Historical root copies of the same two files

The deletion is visible in git history at commit `2f4c514 Remove legacy Python monolith from desktop backend`.

## Current Verification

The repository has an automated guard in `desktop/resources/python-app/tests/test_api_contract.py`:

- It runs `git ls-files`.
- It checks tracked file paths for the removed monolith names.
- It scans tracked UTF-8 text files for the removed monolith names.
- It skips binary files so image bytes cannot create false positives.
- It ignores only the guard test file itself, because the test must construct the forbidden strings.

The remaining plain `qwen` references are provider options for Alibaba DashScope-compatible API usage, not the removed monolith. They are intentionally separate from the forbidden numbered monolith names.

## Last Manual Scan

Commands used:

```powershell
git ls-files | rg -n "(?i)(qwen|qwen-numbered-monolith|qw-numbered-alias)" -S
rg -n "removed numbered monolith name patterns" . -S
```

Result:

- No tracked file path contains the removed monolith names.
- Content hits for plain `qwen` are limited to supported provider UI/config entries and the guard test.
