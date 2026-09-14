#!/usr/bin/env bash
# Shared Git validation checks for DSOxLab.
# Used by Git labs.
#
# Usage (via dispatch): check.sh <check-type> [args...]

_check_git() {
    local check_type="$1"; shift
    case "$check_type" in
    repo-exists)
        local path="${1:?Missing repo path}"
        if [[ -d "$path/.git" ]] || git -C "$path" rev-parse --git-dir &>/dev/null 2>&1; then
            echo "OK: git repo exists at '$path'."
        else
            echo "FAIL: no git repo at '$path'."
            exit 1
        fi
        ;;

    has-commits)
        local path="${1:?Missing repo path}"
        local min="${2:-1}"
        local count
        count=$(git -C "$path" rev-list --count HEAD 2>/dev/null || echo "0")
        if (( count >= min )); then
            echo "OK: repo has $count commits (>= $min)."
        else
            echo "FAIL: repo has $count commits (expected >= $min)."
            exit 1
        fi
        ;;

    branch-exists)
        local path="${1:?Missing repo path}"
        local branch="${2:?Missing branch name}"
        if git -C "$path" rev-parse --verify "$branch" &>/dev/null; then
            echo "OK: branch '$branch' exists."
        else
            echo "FAIL: branch '$branch' not found."
            exit 1
        fi
        ;;

    file-in-repo)
        local path="${1:?Missing repo path}"
        local file="${2:?Missing file path}"
        if git -C "$path" ls-files --error-unmatch "$file" &>/dev/null; then
            echo "OK: '$file' is tracked in repo."
        else
            echo "FAIL: '$file' is not tracked in repo."
            exit 1
        fi
        ;;

    current-branch)
        local path="${1:?Missing repo path}"
        local expected="${2:?Missing expected branch}"
        local current
        current=$(git -C "$path" branch --show-current 2>/dev/null || echo "")
        if [[ "$current" == "$expected" ]]; then
            echo "OK: current branch is '$expected'."
        else
            echo "FAIL: expected branch '$expected', got '$current'."
            exit 1
        fi
        ;;

    tag-exists)
        local path="${1:?Missing repo path}"
        local tag="${2:?Missing tag name}"
        if git -C "$path" rev-parse --verify "refs/tags/$tag" &>/dev/null; then
            echo "OK: tag '$tag' exists."
        else
            echo "FAIL: tag '$tag' not found."
            exit 1
        fi
        ;;

    *) return 2 ;;
    esac
}
