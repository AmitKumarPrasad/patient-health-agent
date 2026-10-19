---
name: project-workflow
description: Follow the Patient Health Agent repository workflow for repeatable development tasks, efficient CI use, failure diagnosis, and automatic sequential task execution.
---

# Patient Health Agent project workflow

Use this skill for every repeatable development task in this repository. Read the root `AGENTS.md` first; its workstream ownership, branch, testing, privacy, review, and merge rules remain authoritative.

## Start each task

1. Identify the next concrete issue or task and its owning workstream.
2. Check `main`, open PRs, current CI runs, and issue dependencies. Do not duplicate an open task.
3. Start a focused feature branch from the latest `main`, using the repository naming convention.
4. Keep scope to one issue and coordinate changes to shared files and API contracts.

## Finish implementation before triggering CI

1. Inspect the relevant code and reproduce the issue before editing.
2. Implement the complete, minimal change, including focused tests and documentation when needed.
3. Review the final diff for correctness, security, privacy, and unintended changes.
4. Run the narrowest relevant local tests, lint, type checks, and build available. Record any unavailable checks honestly.
5. Commit and push the finished candidate once, then let the six required GitHub Actions jobs run: `api`, `web`, `mcp`, `compose`, `backup`, and `e2e`.

Do not push intermediate edits, repeated rebases, or cosmetic changes just to see whether CI passes. Do not update a branch while its checks are running unless a concrete failure requires a fix or the base has become materially stale. Batch related edits and tests before the next push. Never skip a required check to save time.

## When a check fails

1. Identify the failed job and exact failing step from its logs.
2. Reproduce the failure locally where practical; distinguish a code defect from an infrastructure or flaky-test failure.
3. Fix the underlying cause, add or adjust a focused regression test when appropriate, and rerun relevant local checks.
4. Push one corrective commit and inspect the new run. Do not blindly rerun or push speculative fixes.
5. If a check is inconclusive or blocked by infrastructure, report the limitation; do not call the build green.

## Review and merge

- Rebase on latest `main` before merge when needed, then verify the resulting commit has a fresh full set of required checks.
- Require independent review for security-sensitive changes as specified in `AGENTS.md`. A discussion comment by the author is not an approval.
- Merge only when the PR is mergeable, all required checks pass on its current head, and required reviews are present.
- After each merge, refresh `main` and re-evaluate open PRs because their base and mergeability may have changed.

## Continue automatically after a green build

A green build completes the current task's verification; it does not mean the workstream should pause for another user command. Immediately select the next ready, independent issue and begin it, subject to branch ownership and dependencies in `AGENTS.md`.

Before starting the next task, record the previous task's PR, merged/ready status, tested commit, and CI result in the issue or PR discussion when useful. Keep blockers visible so other agents do not repeat failed approaches. If all available tasks depend on a review, decision, secret, or external action that the agent cannot supply, stop that workstream and state the specific blocker while other independent work continues.

## Agent coordination

- Each agent owns one assigned issue and one feature branch; never overwrite another agent's branch.
- Share concise findings, dependencies, blockers, and failure causes in the relevant PR or issue discussion so other agents can act on them.
- Start independent tasks in parallel only when file ownership and dependencies permit it. Avoid competing changes to shared files.
- Use synthetic data only. Never put patient data, credentials, tokens, or secrets into prompts, commits, issues, or CI logs.
- Report progress with concrete branch, commit, test, and CI status; do not claim work or checks that were not performed.
