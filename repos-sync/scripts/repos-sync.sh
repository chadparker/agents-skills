#!/usr/bin/env bash
# Fetch every git repo directly under a directory, report its state, and
# fast-forward the ones that are clean and sitting on the remote default branch.
#
# Usage: repos-sync.sh [--dry-run] [DIR]   (DIR defaults to .)
#
# A repo is pulled only when ALL hold:
#   - current branch is origin's live default branch, tracking origin/<default>
#   - `git status --porcelain` succeeds and is empty (no staged, unstaged, or untracked files)
#   - no merge/rebase/cherry-pick/revert/bisect in progress
#   - upstream is set, repo is behind it, and ahead of it by 0
# The pull is `git merge --ff-only @{u}`: it can only move the branch forward.
# Dirty repositories are always skipped; no reset or stash is performed.

set -u

dry_run=0
root=.
root_set=0
options=1
for arg in "$@"; do
  if [ "$options" -eq 1 ]; then
    case "$arg" in
      --dry-run|-n) dry_run=1; continue ;;
      -h|--help) sed -n '2,/^$/s/^# \{0,1\}//p' "$0"; exit 0 ;;
      --) options=0; continue ;;
      -*) printf 'Unknown option: %s\n' "$arg" >&2; exit 2 ;;
    esac
  fi
  if [ "$root_set" -eq 1 ]; then
    printf 'Only one directory argument is allowed.\n' >&2
    exit 2
  fi
  root=$arg
  root_set=1
done

cd -- "$root" || exit 1

repos=()
for d in */; do
  d=${d%/}
  [ -e "$d/.git" ] && repos+=("$d")
done

if [ ${#repos[@]} -eq 0 ]; then
  echo "No git repos found directly under $(pwd)"
  exit 0
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# Fetch all repos in parallel and read each origin's live default branch.
for d in "${repos[@]}"; do
  (
    if ! GIT_TERMINAL_PROMPT=0 git -C "$d" fetch --all --prune --quiet >"$tmp/$d.fetch" 2>&1; then
      echo failed >"$tmp/$d.fetchfail"
    elif GIT_TERMINAL_PROMPT=0 git -C "$d" ls-remote --symref origin HEAD >"$tmp/$d.head" 2>"$tmp/$d.headerr"; then
      awk '$1 == "ref:" && $3 == "HEAD" && $2 ~ /^refs\/heads\// { sub(/^refs\/heads\//, "", $2); print $2; exit }' "$tmp/$d.head" >"$tmp/$d.default"
    fi
  ) &
done
wait

in_progress() {
  local gd
  gd=$(git -C "$1" rev-parse --absolute-git-dir 2>/dev/null) || return 1
  for f in MERGE_HEAD rebase-merge rebase-apply CHERRY_PICK_HEAD REVERT_HEAD sequencer BISECT_LOG; do
    [ -e "$gd/$f" ] && { echo "${f%_HEAD}"; return 0; }
  done
  return 1
}


out="$tmp/out"
printf 'REPO\tBRANCH\tSTATE\tUPSTREAM\tVS UPSTREAM\tVS DEFAULT\tACTION\n' >"$out"

for d in "${repos[@]}"; do
  branch=$(git -C "$d" symbolic-ref --quiet --short HEAD 2>/dev/null) || branch="(detached)"
  def=$(cat "$tmp/$d.default" 2>/dev/null)
  if porcelain=$(git -C "$d" status --porcelain --untracked-files=all --ignore-submodules=none 2>/dev/null); then
    dirty=$(printf '%s' "$porcelain" | grep -c .)
  else
    dirty=unknown
  fi
  op=$(in_progress "$d")

  state=clean
  if [ "$dirty" = unknown ]; then
    state="status unknown"
  elif [ "$dirty" -gt 0 ]; then
    state="dirty($dirty)"
  fi
  [ -n "$op" ] && state="$state,$op"

  up="-"; upstream="-"; ahead=0; behind=0; upref=""; count_failed=0
  has_origin=0
  git -C "$d" remote get-url origin >/dev/null 2>&1 && has_origin=1
  if [ "$branch" != "(detached)" ] && git -C "$d" rev-parse --quiet --verify '@{u}' >/dev/null 2>&1; then
    upref=$(git -C "$d" rev-parse --symbolic-full-name '@{u}' 2>/dev/null)
    upstream=${upref#refs/remotes/}
    if read -r ahead behind < <(git -C "$d" rev-list --left-right --count 'HEAD...@{u}') \
       && [[ "$ahead" =~ ^[0-9]+$ && "$behind" =~ ^[0-9]+$ ]]; then
      up="+$ahead/-$behind"
    else
      ahead=0; behind=0; count_failed=1
      up="?"
    fi
  elif [ "$branch" != "(detached)" ]; then
    if [ "$has_origin" -eq 1 ]; then
      upstream="no upstream"
      up="no upstream"
    else
      upstream="no origin"
      up="no origin"
    fi
  fi

  vsdef="-"
  if [ -n "$def" ] && [ "$branch" != "$def" ] \
     && git -C "$d" show-ref --verify --quiet "refs/remotes/origin/$def"; then
    if read -r a b < <(git -C "$d" rev-list --left-right --count "HEAD...origin/$def") \
       && [[ "$a" =~ ^[0-9]+$ && "$b" =~ ^[0-9]+$ ]]; then
      vsdef="+$a/-$b $def"
    else
      vsdef="? $def"
    fi
  fi

  action="-"
  if [ -e "$tmp/$d.fetchfail" ]; then
    action="FETCH FAILED"
  elif [ "$branch" = "(detached)" ]; then
    action="skip: detached"
  elif [ "$has_origin" -eq 0 ]; then
    action="skip: no origin"
  elif [ -z "$def" ]; then
    action="skip: default unknown"
  elif [ "$branch" != "$def" ]; then
    action="skip: non-default branch"
  elif [ "$dirty" = unknown ]; then
    action="skip: status failed"
  elif [ "$count_failed" -eq 1 ]; then
    action="skip: count failed"
  elif [ "$state" != clean ]; then
    action="skip: not clean"
  elif [ "$up" = "no upstream" ]; then
    action="skip: no upstream"
  elif [ "$upref" != "refs/remotes/origin/$def" ]; then
    action="skip: upstream ${upref#refs/remotes/}"
  elif [ "$behind" -gt 0 ] && [ "$ahead" -gt 0 ]; then
    action="skip: diverged"
  elif [ "$behind" -gt 0 ]; then
    if [ $dry_run -eq 1 ]; then
      action="would pull $behind"
    elif git -C "$d" merge --ff-only --no-overwrite-ignore --quiet '@{u}' >"$tmp/$d.merge" 2>&1; then
      action="pulled $behind"
      up="+0/-0"
    else
      action="PULL FAILED"
    fi
  fi

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$d" "$branch" "$state" "$upstream" "$up" "$vsdef" "$action" >>"$out"
done

column -t -s "$(printf '\t')" "$out"

# Surface error output so failures are explainable.
for d in "${repos[@]}"; do
  for kind in fetch headerr merge; do
    f="$tmp/$d.$kind"
    if [ -s "$f" ] && { [ "$kind" = merge ] || [ "$kind" = headerr ] || [ -e "$tmp/$d.fetchfail" ]; }; then
      echo
      echo "--- $d ($kind) ---"
      cat "$f"
    fi
  done
done
