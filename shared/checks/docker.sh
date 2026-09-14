#!/usr/bin/env bash
# Shared Docker/Podman validation checks for DSOxLab.
# Used by Docker containerization labs.
#
# Usage (via dispatch): check.sh <check-type> [args...]

_DOCKER_ENGINE="${KXL_CONTAINER_ENGINE:-docker}"

_check_docker() {
    local check_type="$1"; shift
    case "$check_type" in
    image-exists)
        local image="${1:?Missing image name}"
        if $_DOCKER_ENGINE image inspect "$image" &>/dev/null; then
            echo "OK: image '$image' exists."
        else
            echo "FAIL: image '$image' not found."
            exit 1
        fi
        ;;

    image-user)
        local image="${1:?Missing image name}"
        local expected_user="${2:?Missing expected user}"
        local user
        user=$($_DOCKER_ENGINE inspect --format '{{.Config.User}}' "$image" 2>/dev/null || echo "")
        if [[ "$user" == "$expected_user" ]]; then
            echo "OK: image user is '$expected_user'."
        else
            echo "FAIL: expected user '$expected_user', got '$user'."
            exit 1
        fi
        ;;

    image-size-max-mb)
        local image="${1:?Missing image name}"
        local max_mb="${2:?Missing max size in MB}"
        local size_bytes
        size_bytes=$($_DOCKER_ENGINE inspect --format '{{.Size}}' "$image" 2>/dev/null || echo "999999999")
        local size_mb=$((size_bytes / 1048576))
        if (( size_mb <= max_mb )); then
            echo "OK: image '$image' is ${size_mb}MB (<= ${max_mb}MB)."
        else
            echo "FAIL: image '$image' is ${size_mb}MB (max ${max_mb}MB)."
            exit 1
        fi
        ;;

    image-layers-max)
        local image="${1:?Missing image name}"
        local max_layers="${2:?Missing max layers}"
        local layers
        layers=$($_DOCKER_ENGINE inspect --format '{{len .RootFS.Layers}}' "$image" 2>/dev/null || echo "999")
        if (( layers <= max_layers )); then
            echo "OK: image '$image' has $layers layers (<= $max_layers)."
        else
            echo "FAIL: image '$image' has $layers layers (max $max_layers)."
            exit 1
        fi
        ;;

    image-healthcheck)
        local image="${1:?Missing image name}"
        local hc
        hc=$($_DOCKER_ENGINE inspect --format '{{json .Config.Healthcheck}}' "$image" 2>/dev/null || echo "null")
        if [[ "$hc" != "null" && -n "$hc" ]] && echo "$hc" | grep -q "Test"; then
            echo "OK: image has a healthcheck."
        else
            echo "FAIL: image has no healthcheck."
            exit 1
        fi
        ;;

    image-expose)
        local image="${1:?Missing image name}"
        local expected_port="${2:?Missing expected port}"
        local ports
        ports=$($_DOCKER_ENGINE inspect --format '{{json .Config.ExposedPorts}}' "$image" 2>/dev/null || echo "{}")
        if echo "$ports" | grep -q "$expected_port"; then
            echo "OK: image exposes port $expected_port."
        else
            echo "FAIL: image does not expose port $expected_port."
            exit 1
        fi
        ;;

    container-running)
        local name="${1:?Missing container name}"
        local state
        state=$($_DOCKER_ENGINE inspect --format '{{.State.Running}}' "$name" 2>/dev/null || echo "false")
        if [[ "$state" == "true" ]]; then
            echo "OK: container '$name' is running."
        else
            echo "FAIL: container '$name' is not running."
            exit 1
        fi
        ;;

    container-exists)
        local name="${1:?Missing container name}"
        if $_DOCKER_ENGINE inspect "$name" &>/dev/null; then
            echo "OK: container '$name' exists."
        else
            echo "FAIL: container '$name' not found."
            exit 1
        fi
        ;;

    docker-port)
        local name="${1:?Missing container name}"
        local expected_port="${2:?Missing expected port}"
        local ports
        ports=$($_DOCKER_ENGINE port "$name" 2>/dev/null || echo "")
        if echo "$ports" | grep -q "$expected_port"; then
            echo "OK: container '$name' exposes port $expected_port."
        else
            echo "FAIL: container '$name' does not expose port $expected_port."
            exit 1
        fi
        ;;

    container-volume)
        local name="${1:?Missing container name}"
        local expected_mount="${2:?Missing expected mount path}"
        local mounts
        mounts=$($_DOCKER_ENGINE inspect --format '{{json .Mounts}}' "$name" 2>/dev/null || echo "[]")
        if echo "$mounts" | grep -q "$expected_mount"; then
            echo "OK: container '$name' has mount for '$expected_mount'."
        else
            echo "FAIL: container '$name' has no mount for '$expected_mount'."
            exit 1
        fi
        ;;

    container-user)
        local name="${1:?Missing container name}"
        local expected_user="${2:?Missing expected user}"
        local user
        user=$($_DOCKER_ENGINE inspect --format '{{.Config.User}}' "$name" 2>/dev/null || echo "")
        if [[ "$user" == "$expected_user" ]]; then
            echo "OK: container user is '$expected_user'."
        else
            echo "FAIL: expected user '$expected_user', got '$user'."
            exit 1
        fi
        ;;

    compose-service-running)
        local service="${1:?Missing service name}"
        local project="${2:-}"
        local state
        if [[ -n "$project" ]]; then
            state=$($_DOCKER_ENGINE compose -p "$project" ps --format '{{.Service}} {{.State}}' 2>/dev/null | grep "^$service " | awk '{print $2}')
        else
            state=$($_DOCKER_ENGINE compose ps --format '{{.Service}} {{.State}}' 2>/dev/null | grep "^$service " | awk '{print $2}')
        fi
        if [[ "$state" == "running" ]]; then
            echo "OK: service '$service' is running."
        else
            echo "FAIL: service '$service' is not running (state: $state)."
            exit 1
        fi
        ;;

    *) return 2 ;;
    esac
}
