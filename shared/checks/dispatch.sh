#!/usr/bin/env bash
# DSOxLab — Shared validation dispatcher.
# Sources all check modules and routes check-type to the right handler.
#
# Usage: source dispatch.sh; _dispatch <check-type> [args...]
#   Or:  bash dispatch.sh <check-type> [args...]

set -euo pipefail

_CHECKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source all check modules
source "$_CHECKS_DIR/base.sh"
source "$_CHECKS_DIR/k8s.sh"
source "$_CHECKS_DIR/docker.sh"
source "$_CHECKS_DIR/git.sh"
source "$_CHECKS_DIR/linux.sh"

_dispatch() {
    local check_type="${1:?Missing check-type argument}"
    shift

    # Try each module in order; each returns 2 for unknown type
    _check_base "$check_type" "$@" && return 0
    local rc=$?; [[ $rc -ne 2 ]] && return $rc

    _check_k8s "$check_type" "$@" && return 0
    rc=$?; [[ $rc -ne 2 ]] && return $rc

    _check_docker "$check_type" "$@" && return 0
    rc=$?; [[ $rc -ne 2 ]] && return $rc

    _check_git "$check_type" "$@" && return 0
    rc=$?; [[ $rc -ne 2 ]] && return $rc

    _check_linux "$check_type" "$@" && return 0
    rc=$?; [[ $rc -ne 2 ]] && return $rc

    echo "ERROR: unknown check-type '$check_type'"
    exit 1
}

# Allow direct invocation: bash dispatch.sh <check-type> [args...]
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    _dispatch "$@"
fi
