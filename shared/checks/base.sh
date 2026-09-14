#!/usr/bin/env bash
# Shared base validation checks for DSOxLab.
# Generic file/directory/script checks used across all lab types.
#
# Usage (via dispatch): check.sh <check-type> [args...]

_check_base() {
    local check_type="$1"; shift
    case "$check_type" in
    file-exists)
        local path="${1:?Missing path}"
        if [[ -f "$path" ]]; then
            echo "OK: file '$path' exists."
        else
            echo "FAIL: file '$path' not found."
            exit 1
        fi
        ;;

    dir-exists)
        local path="${1:?Missing path}"
        if [[ -d "$path" ]]; then
            echo "OK: directory '$path' exists."
        else
            echo "FAIL: directory '$path' not found."
            exit 1
        fi
        ;;

    file-contains)
        local path="${1:?Missing path}"
        local expected="${2:?Missing expected content}"
        if [[ ! -f "$path" ]]; then
            echo "FAIL: file '$path' not found."
            exit 1
        fi
        if grep -q "$expected" "$path"; then
            echo "OK: '$path' contains '$expected'."
        else
            echo "FAIL: '$path' does not contain '$expected'."
            exit 1
        fi
        ;;

    file-content)
        local path="${1:?Missing path}"
        local expected="${2:?Missing expected content}"
        if [[ ! -f "$path" ]]; then
            echo "FAIL: file '$path' not found."
            exit 1
        fi
        local actual
        actual=$(cat "$path")
        if [[ "$actual" == *"$expected"* ]]; then
            echo "OK: '$path' contains expected content."
        else
            echo "FAIL: '$path' does not contain expected content."
            exit 1
        fi
        ;;

    file-has-content)
        local path="${1:?Missing path}"
        local expected="${2:?Missing expected content}"
        if [[ ! -f "$path" ]]; then
            echo "FAIL: file '$path' not found."
            exit 1
        fi
        if grep -q "$expected" "$path"; then
            echo "OK: '$path' has expected content."
        else
            echo "FAIL: '$path' does not have expected content."
            exit 1
        fi
        ;;

    file-perms)
        local path="${1:?Missing path}"
        local expected="${2:?Missing expected permissions}"
        if [[ ! -e "$path" ]]; then
            echo "FAIL: '$path' does not exist."
            exit 1
        fi
        local actual
        actual=$(stat -c '%a' "$path" 2>/dev/null)
        if [[ "$actual" == "$expected" ]]; then
            echo "OK: '$path' has permissions $expected."
        else
            echo "FAIL: '$path' has permissions $actual, expected $expected."
            exit 1
        fi
        ;;

    script-output)
        local path="${1:?Missing script path}"
        local expected="${2:?Missing expected output}"
        if [[ ! -x "$path" ]]; then
            echo "FAIL: '$path' is not executable."
            exit 1
        fi
        local actual
        actual=$("$path" 2>&1)
        if echo "$actual" | grep -q "$expected"; then
            echo "OK: script outputs '$expected'."
        else
            echo "FAIL: expected output '$expected', got '$actual'."
            exit 1
        fi
        ;;

    python-runs)
        local script="${1:?Missing script path}"
        shift
        if python3 "$script" "$@" &>/dev/null; then
            echo "OK: '$script' runs successfully."
        else
            echo "FAIL: '$script' failed to run."
            exit 1
        fi
        ;;

    python-output)
        local script="${1:?Missing script path}"
        local expected="${2:?Missing expected output}"
        shift 2
        local actual
        actual=$(python3 "$script" "$@" 2>&1)
        if echo "$actual" | grep -q "$expected"; then
            echo "OK: script output contains '$expected'."
        else
            echo "FAIL: expected '$expected', got '$actual'."
            exit 1
        fi
        ;;

    service-active)
        local service="${1:?Missing service name}"
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            echo "OK: service '$service' is active."
        else
            echo "FAIL: service '$service' is not active."
            exit 1
        fi
        ;;

    perms-readable-all)
        local path="${1:?Missing path}"
        if [[ ! -e "$path" ]]; then
            echo "FAIL: '$path' does not exist."
            exit 1
        fi
        local mode
        mode=$(stat -c '%a' "$path")
        local world_digit=$(( mode % 10 ))
        if (( world_digit >= 4 )); then
            echo "OK: '$path' is readable by all (mode $mode)."
        else
            echo "FAIL: '$path' is not world-readable (mode $mode)."
            exit 1
        fi
        ;;

    perms-executable)
        local path="${1:?Missing path}"
        if [[ ! -e "$path" ]]; then
            echo "FAIL: '$path' does not exist."
            exit 1
        fi
        if [[ -x "$path" ]]; then
            echo "OK: '$path' is executable."
        else
            echo "FAIL: '$path' is not executable."
            exit 1
        fi
        ;;

    file-not-contains)
        local path="${1:?Missing path}"
        local pattern="${2:?Missing pattern}"
        if [[ ! -f "$path" ]]; then
            echo "FAIL: file '$path' not found."
            exit 1
        fi
        if grep -q "$pattern" "$path"; then
            echo "FAIL: '$path' still contains '$pattern'."
            exit 1
        else
            echo "OK: '$path' does not contain '$pattern'."
        fi
        ;;

    *) return 2 ;;
    esac
}
