# GitHub to GitLab CI mirror verification

This documentation change is a non-production smoke test for GitHub-to-GitLab pull mirroring.

Verification checklist:

1. Confirm this commit appears in the GitLab project's default branch after the mirror updates.
2. Confirm GitLab creates a pipeline for the mirrored commit.
3. Verify API, MCP, web, validation, and end-to-end jobs complete successfully.
4. Keep GitHub Actions configured until GitLab CI has been verified.

A successful GitHub commit alone does not prove GitLab mirroring or CI execution.
