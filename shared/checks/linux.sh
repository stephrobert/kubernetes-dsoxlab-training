#!/usr/bin/env bash
# Shared Linux-specific validation checks for DSOxLab.
# Provides checks for filesystem operations, ACL, and package management.
#
# Usage (via dispatch): check.sh <check-type> [args...]

_check_linux() {
    local check_type="$1"; shift
    case "$check_type" in
    no-txt-files)
        local dir="${1:?Missing directory}"
        local remaining
        remaining=$(find "$dir" -name "*.txt" 2>/dev/null | wc -l)
        if [[ "$remaining" -eq 0 ]]; then
            echo "OK: no .txt files remain in '$dir'."
        else
            echo "FAIL: $remaining .txt file(s) still exist in '$dir'."
            find "$dir" -name "*.txt"
            exit 1
        fi
        ;;

    awk-output-contains)
        local awk_script="${1:?Missing awk script path}"
        local input_file="${2:?Missing input file}"
        local expected="${3:?Missing expected pattern}"
        if [[ ! -f "$awk_script" ]]; then
            echo "FAIL: awk script '$awk_script' not found."
            exit 1
        fi
        if [[ ! -f "$input_file" ]]; then
            echo "FAIL: input file '$input_file' not found."
            exit 1
        fi
        local output
        output=$(awk -f "$awk_script" "$input_file" 2>&1)
        if echo "$output" | grep -q "$expected"; then
            echo "OK: awk output contains '$expected'."
        else
            echo "FAIL: awk output does not contain '$expected'. Got: $output"
            exit 1
        fi
        ;;

    acl-contains)
        local path="${1:?Missing path}"
        local entry="${2:?Missing ACL entry}"
        if [[ ! -e "$path" ]]; then
            echo "FAIL: '$path' does not exist."
            exit 1
        fi
        local output
        output=$(getfacl "$path" 2>&1)
        if echo "$output" | grep -qF "$entry"; then
            echo "OK: '$path' has ACL entry '$entry'."
        else
            echo "FAIL: '$path' does not have ACL entry '$entry'."
            echo "Current ACLs: $output"
            exit 1
        fi
        ;;

    acl-default-contains)
        local path="${1:?Missing path}"
        local entry="${2:?Missing ACL entry}"
        if [[ ! -d "$path" ]]; then
            echo "FAIL: '$path' is not a directory or does not exist."
            exit 1
        fi
        local output
        output=$(getfacl -d "$path" 2>&1)
        if echo "$output" | grep -qF "$entry"; then
            echo "OK: '$path' has default ACL entry '$entry'."
        else
            echo "FAIL: '$path' does not have default ACL entry '$entry'."
            echo "Current default ACLs: $output"
            exit 1
        fi
        ;;

    pkg-version-starts)
        local pkg="${1:?Missing package name}"
        local version_prefix="${2:?Missing version prefix}"
        local installed_version
        installed_version=$(dpkg -l "$pkg" 2>/dev/null | awk '/^ii/{print $3}' | head -1)
        if [[ -z "$installed_version" ]]; then
            echo "FAIL: package '$pkg' is not installed."
            exit 1
        fi
        if [[ "$installed_version" == ${version_prefix}* ]]; then
            echo "OK: '$pkg' is installed at version '$installed_version'."
        else
            echo "FAIL: '$pkg' version '$installed_version' does not start with '$version_prefix'."
            exit 1
        fi
        ;;

    *) return 2 ;;
    esac
}
