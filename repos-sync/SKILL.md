---
name: repos-sync
description: Fetch every repo in a multi-repo directory, report branch/dirty/behind status, and fast-forward clean repos on the remote default branch.
disable-model-invocation: true
metadata:
  author: Chad Parker
  source: local
  license: MIT
---

Run the bundled script from the directory holding the repos (or pass it as an argument):

```bash
~/.agents/skills/repos-sync/scripts/repos-sync.sh [--dry-run] [DIR]
```

- Run it fully unsandboxed (Cursor: `required_permissions: ["all"]`). The sandbox blocks writes under `.claude/`/`.cursor/`, which can leave a fast-forward half-applied. If you cannot run unsandboxed, give the user the command to run in their own terminal. `--dry-run` still fetches and prunes remote-tracking refs, so it also needs permission to write Git metadata.
- `--dry-run` fetches and reports only (`would pull N`); it does not merge or change working files. Use it when the user says "status", "check", or "don't pull".
- It looks only at direct children of DIR.

## The pull rule

The script pulls a repo (`git merge --ff-only @{u}`) only when it is **on origin's live default branch** (verified via `git ls-remote --symref origin HEAD`) and tracking `origin/<default>`, **clean** (`git status --porcelain` succeeds and is empty, untracked files included), has no merge/rebase in progress, and is strictly behind its upstream. If the default cannot be determined, it skips the repo rather than guessing. Dirty repositories are always skipped, even when their changes match upstream. The script never runs `git reset`.

Every discovered repo is fetched and pruned, updating its remote-tracking refs. Repos that do not meet the pull rule are not merged, checked out, stashed, or reset; this includes `main`/`develop` when they are not the default. Leave any further change to a repo (rebasing a feature branch, pulling a dirty repo) to the user, and offer it as a follow-up.
## Report

After the script's table, write a short summary grouped by `ACTION`:

1. **Pulled**: every `pulled N` and `would pull N`, repo names and commit counts, on one line.
2. **Needs attention**: every `* FAILED` and every `skip:` except `skip: non-default branch`. One line per repo; add extra column facts (`STATE`, `UPSTREAM`, diverge counts) when they apply. `skip: no origin` means no `origin` remote; `skip: no upstream` means `origin` exists but this branch has no `@{u}`.
3. **Non-default branches**: every `skip: non-default branch`, each with its `VS DEFAULT` count. Flag the ones far behind default as rebase candidates.

Leave out a repo only when `ACTION` is `-` and `STATE` is `clean`.
