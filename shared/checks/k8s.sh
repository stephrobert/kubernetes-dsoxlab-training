#!/usr/bin/env bash
# Shared Kubernetes validation checks for DSOxLab.
# Auto-sourced by labs/shared/checks/dispatch.sh
# Contains all K8s check-types used across CKAD/CKA/CKS labs.
#
# Usage (via dispatch): check.sh <check-type> [args...]

_check_k8s() {
    local check_type="$1"; shift
    # Default manifest path used by apiserver-flag checks
    local MANIFEST="${MANIFEST:-/etc/kubernetes/manifests/kube-apiserver.yaml}"
    case "$check_type" in
    all-nodes-ready)
        not_ready=$(kubectl get nodes --no-headers 2>/dev/null | grep -v " Ready " || true)
        if [[ -z "$not_ready" ]]; then echo "All nodes are Ready."
        else echo "Some nodes are not Ready: $not_ready"; exit 1; fi
        ;;

    all-nodes-schedulable)
                unschedulable=$(kubectl get nodes -o json 2>/dev/null | python3 -c "
import sys, json
nodes = json.load(sys.stdin)
for n in nodes['items']:
    if n['spec'].get('unschedulable', False):
        print(n['metadata']['name']); sys.exit(1)
print('all schedulable')
")
                if [[ "$unschedulable" == "all schedulable" ]]; then echo "All nodes are schedulable."
                else echo "Node '$unschedulable' is still cordoned."; exit 1; fi
        ;;

    apiserver-flag)
        flag="${1:?Missing flag}"
        if ssh master1 "sudo grep -q -- '$flag' $MANIFEST" 2>/dev/null; then
            echo "API server flag '$flag' found."
        else echo "API server flag '$flag' not found."; exit 1; fi
        ;;

    apiserver-flag-contains)
        flag_prefix="${1:?Missing flag prefix}"; value="${2:?Missing value}"
        line=$(ssh master1 "sudo grep -- '$flag_prefix' $MANIFEST" 2>/dev/null || echo "")
        if echo "$line" | grep -q "$value"; then
            echo "Flag '$flag_prefix' contains '$value'."
        else echo "Flag '$flag_prefix' does not contain '$value'."; exit 1; fi
        ;;

    apparmor-profile-loaded)
        profile="${1:?Missing profile name}"
        if ssh worker1 "sudo aa-status 2>/dev/null | grep -q '$profile'" 2>/dev/null; then
            echo "AppArmor profile '$profile' is loaded."
        else echo "AppArmor profile '$profile' not loaded."; exit 1; fi
        ;;

    auth-can-i)
        ns="${1:?Missing namespace}"; user="${2:?Missing user}"
        verb="${3:?Missing verb}"; resource="${4:?Missing resource}"; expected="${5:?Missing yes/no}"
        _raw=$(kubectl auth can-i "$verb" "$resource" -n "$ns" --as="$user" 2>/dev/null || echo "no")
        result=$(echo "$_raw" | head -1)
        if [[ "$result" == "$expected" ]]; then echo "auth can-i $verb $resource --as=$user = $expected."
        else echo "auth can-i $verb $resource --as=$user: expected '$expected', got '$result'."; exit 1; fi
        ;;

    can-i)
        ns="${1:?Missing namespace}"
        sa="${2:?Missing serviceaccount name}"
        verb="${3:?Missing verb}"
        resource="${4:?Missing resource}"
        expected="${5:?Missing expected (yes/no)}"

        result=$(kubectl auth can-i "$verb" "$resource" \
            --as="system:serviceaccount:${ns}:${sa}" \
            -n "$ns" 2>/dev/null || true)
        if [[ "$result" == "$expected" ]]; then
            echo "ServiceAccount '$sa' can-i $verb $resource = $expected."
        else
            echo "ServiceAccount '$sa' can-i $verb $resource = $result, expected $expected."
            exit 1
        fi
        ;;

    capabilities-drop-all)
                ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"
                kubectl get pod "$pod" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
pod = json.load(sys.stdin)
sc = pod['spec']['containers'][0].get('securityContext', {})
caps = sc.get('capabilities', {})
drop = caps.get('drop', [])
if 'ALL' in drop:
    print('Capabilities drop ALL found.'); sys.exit(0)
print('Capabilities drop ALL not found. Got: ' + str(drop)); sys.exit(1)
"
        ;;

    configmap-data)
        ns="${1:?Missing namespace}"
        cm="${2:?Missing configmap name}"
        expected="${3:?Missing expected data (comma-separated key=value)}"

        if ! kubectl get configmap "$cm" -n "$ns" &>/dev/null; then
            echo "ConfigMap '$cm' not found in namespace '$ns'."
            exit 1
        fi

        IFS=',' read -ra ENTRIES <<< "$expected"
        for entry in "${ENTRIES[@]}"; do
            key="${entry%%=*}"
            value="${entry#*=}"
            actual=$(kubectl get configmap "$cm" -n "$ns" \
                -o jsonpath="{.data.$key}" 2>/dev/null)
            if [[ "$actual" != "$value" ]]; then
                echo "ConfigMap '$cm' key '$key': expected '$value', got '$actual'."
                exit 1
            fi
        done
        echo "ConfigMap '$cm' has all expected data."
        ;;

    configmap-key-exists)
        ns="${1:?Missing namespace}"; cm="${2:?Missing configmap}"; key="${3:?Missing key}"
        val=$(kubectl get configmap "$cm" -n "$ns" -o json 2>/dev/null \
            | python3 -c "import sys,json; d=json.load(sys.stdin).get('data',{}); print(d.get('$key',''))" \
            2>/dev/null || echo "")
        if [[ -n "$val" ]]; then echo "ConfigMap $cm has key '$key'."
        else echo "ConfigMap $cm key '$key' is empty."; exit 1; fi
        ;;

    configmap-key-not-empty)
        ns="${1:?Missing namespace}"; cm="${2:?Missing configmap}"; key="${3:?Missing key}"
        val=$(kubectl get configmap "$cm" -n "$ns" -o json 2>/dev/null \
            | python3 -c "import sys,json; d=json.load(sys.stdin).get('data',{}); print(d.get('$key',''))" \
            2>/dev/null || echo "")
        if [[ -n "$val" ]]; then echo "ConfigMap $cm key '$key' has content."
        else echo "ConfigMap $cm key '$key' is empty or missing."; exit 1; fi
        ;;

    configmap-keys)
        ns="${1:?Missing namespace}"; cm="${2:?Missing configmap}"; keys="${3:?Missing keys}"
        IFS=',' read -ra KEYS <<< "$keys"
        for key in "${KEYS[@]}"; do
            val=$(kubectl get configmap "$cm" -n "$ns" -o jsonpath="{.data.$key}" 2>/dev/null || echo "")
            if [[ -z "$val" ]]; then
                echo "ConfigMap '$cm' missing key '$key'."; exit 1
            fi
        done
        echo "All expected keys found in ConfigMap '$cm'."
        ;;

    configmap-value)
        ns="${1:?Missing namespace}"; cm="${2:?Missing configmap}"
        key="${3:?Missing key}"; expected="${4:?Missing value}"
        actual=$(kubectl get configmap "$cm" -n "$ns" -o jsonpath="{.data.$key}" 2>/dev/null || echo "")
        if [[ "$actual" == "$expected" ]]; then echo "ConfigMap $cm.$key = $expected."
        else echo "ConfigMap $cm.$key: expected '$expected', got '$actual'."; exit 1; fi
        ;;

    configmap-value-contains)
        ns="${1:?Missing namespace}"; cm="${2:?Missing configmap}"
        key="${3:?Missing key}"; expected="${4:?Missing value}"
        val=$(kubectl get configmap "$cm" -n "$ns" -o jsonpath="{.data.$key}" 2>/dev/null || echo "")
        if echo "$val" | grep -q "$expected"; then
            echo "ConfigMap $cm key '$key' contains '$expected'."
        else echo "ConfigMap $cm key '$key' does not contain '$expected'."; exit 1; fi
        ;;

    configmap-value-not-contains)
        ns="${1:?Missing namespace}"; cm="${2:?Missing configmap}"
        key="${3:?Missing key}"; forbidden="${4:?Missing value}"
        val=$(kubectl get configmap "$cm" -n "$ns" -o jsonpath="{.data.$key}" 2>/dev/null || echo "")
        if echo "$val" | grep -q "$forbidden"; then
            echo "ConfigMap $cm key '$key' still contains '$forbidden'."; exit 1
        else echo "ConfigMap $cm key '$key' does not contain '$forbidden'."; fi
        ;;

    container-caps-drop-all)
        ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"
        drops=$(kubectl get pod "$pod" -n "$ns" -o json 2>/dev/null | \
          python3 -c "import sys,json;sc=json.load(sys.stdin)['spec']['containers'][0].get('securityContext',{});caps=sc.get('capabilities',{}).get('drop',[]);print(','.join(caps))" 2>/dev/null || echo "")
        if echo "$drops" | grep -qi "ALL"; then echo "Container drops ALL capabilities."
        else echo "Container does not drop ALL caps (drops: $drops)."; exit 1; fi
        ;;

    container-count)
        ns="${1:?Missing namespace}"
        pod="${2:?Missing pod name}"
        expected="${3:?Missing expected count}"
        actual=$(kubectl get pod "$pod" -n "$ns" \
            -o jsonpath='{.spec.containers}' 2>/dev/null | python3 -c "import sys,json;print(len(json.load(sys.stdin)))")
        if [[ "$actual" == "$expected" ]]; then
            echo "Pod '$pod' has $actual containers."
        else
            echo "Pod '$pod' has $actual containers, expected $expected."
            exit 1
        fi
        ;;

    container-exists)
                ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"; cname="${3:?Missing container}"
                kubectl get pod "$pod" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
pod = json.load(sys.stdin)
for c in pod['spec'].get('containers', []):
    if c['name'] == '$cname':
        print('Container found.'); sys.exit(0)
print('Container not found.'); sys.exit(1)
"
        ;;

    container-port)
                ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"; port="${3:?Missing port}"
                kubectl get pod "$pod" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
pod = json.load(sys.stdin)
for c in pod['spec']['containers']:
    for p in c.get('ports', []):
        if str(p.get('containerPort')) == '$port':
            print('Port $port declared.'); sys.exit(0)
print('Port $port not found.'); sys.exit(1)
" 2>/dev/null
        ;;

    container-resources)
                ns="${1:?Missing namespace}"
                pod="${2:?Missing pod name}"
                container="${3:?Missing container name}"
                req_cpu="${4:?Missing requests.cpu}"
                req_mem="${5:?Missing requests.memory}"
                lim_cpu="${6:?Missing limits.cpu}"
                lim_mem="${7:?Missing limits.memory}"

                json=$(kubectl get pod "$pod" -n "$ns" -o json 2>/dev/null)
                result=$(echo "$json" | python3 -c "
import sys, json
pod = json.load(sys.stdin)
for c in pod['spec']['containers']:
    if c['name'] == '$container':
        res = c.get('resources', {})
        req = res.get('requests', {})
        lim = res.get('limits', {})
        errors = []
        if req.get('cpu') != '$req_cpu': errors.append(f\"requests.cpu={req.get('cpu')} expected $req_cpu\")
        if req.get('memory') != '$req_mem': errors.append(f\"requests.memory={req.get('memory')} expected $req_mem\")
        if lim.get('cpu') != '$lim_cpu': errors.append(f\"limits.cpu={lim.get('cpu')} expected $lim_cpu\")
        if lim.get('memory') != '$lim_mem': errors.append(f\"limits.memory={lim.get('memory')} expected $lim_mem\")
        if errors:
            print('; '.join(errors))
            sys.exit(1)
        print('ok')
        sys.exit(0)
print(f'Container $container not found')
sys.exit(1)
" 2>/dev/null || true)
                if [[ "$result" == "ok" ]]; then
                    echo "Container '$container' has correct resources."
                else
                    echo "Container '$container': $result"
                    exit 1
                fi
        ;;

    container-security-field)
                ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"
                field="${3:?Missing field}"; expected="${4:?Missing expected value}"
                actual=$(kubectl get pod "$pod" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
pod = json.load(sys.stdin)
sc = pod['spec']['containers'][0].get('securityContext', {})
v = sc.get('$field', '')
print(str(v).lower() if isinstance(v, bool) else str(v))
")
                if [[ "$actual" == "$expected" ]]; then echo "Container securityContext.$field = $expected."
                else echo "Container securityContext.$field: expected '$expected', got '$actual'."; exit 1; fi
        ;;

    coredns-running)
        ready=$(kubectl get pods -n kube-system -l k8s-app=kube-dns \
            --no-headers 2>/dev/null | awk '$3 == "Running" {count++} END {print count+0}')
        if (( ready >= 1 )); then
            echo "CoreDNS has $ready running pod(s)."
        else
            echo "CoreDNS has no running pods."
            exit 1
        fi
        ;;

    cronjob-history-limit)
        ns="${1:?Missing namespace}"
        cj="${2:?Missing cronjob name}"
        expected="${3:?Missing expected limit}"

        actual=$(kubectl get cronjob "$cj" -n "$ns" \
            -o jsonpath='{.spec.successfulJobsHistoryLimit}' 2>/dev/null)
        if [[ "$actual" == "$expected" ]]; then
            echo "CronJob '$cj' successfulJobsHistoryLimit=$actual."
        else
            echo "CronJob '$cj' successfulJobsHistoryLimit=$actual, expected $expected."
            exit 1
        fi
        ;;

    cronjob-schedule)
        ns="${1:?Missing namespace}"
        cj="${2:?Missing cronjob name}"
        expected="${3:?Missing expected schedule}"

        if ! kubectl get cronjob "$cj" -n "$ns" &>/dev/null; then
            echo "CronJob '$cj' not found in namespace '$ns'."
            exit 1
        fi

        actual=$(kubectl get cronjob "$cj" -n "$ns" \
            -o jsonpath='{.spec.schedule}' 2>/dev/null)
        if [[ "$actual" == "$expected" ]]; then
            echo "CronJob '$cj' has schedule '$actual'."
        else
            echo "CronJob '$cj' schedule: '$actual', expected '$expected'."
            exit 1
        fi
        ;;

    daemonset-all-nodes)
                ns="${1:?Missing namespace}"; ds="${2:?Missing daemonset}"
                kubectl get daemonset "$ds" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
ds = json.load(sys.stdin)
desired = ds['status'].get('desiredNumberScheduled', 0)
ready = ds['status'].get('numberReady', 0)
if desired == 0:
    print('No nodes scheduled.'); sys.exit(1)
if ready >= desired:
    print(f'DaemonSet running on all {desired} nodes.')
else:
    print(f'DaemonSet ready {ready}/{desired}.'); sys.exit(1)
"
        ;;

    daemonset-exists)
        ns="${1:?Missing namespace}"; ds="${2:?Missing daemonset}"
        if kubectl get daemonset "$ds" -n "$ns" &>/dev/null; then echo "DaemonSet '$ds' exists."
        else echo "DaemonSet '$ds' not found."; exit 1; fi
        ;;

    daemonset-pod-label)
                ns="${1:?Missing namespace}"; ds="${2:?Missing daemonset}"; expected="${3:?Missing label}"
                key="${expected%%=*}"; value="${expected#*=}"
                kubectl get daemonset "$ds" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
ds = json.load(sys.stdin)
labels = ds['spec']['template']['metadata'].get('labels', {})
if labels.get('$key') == '$value':
    print('Label $expected found.'); sys.exit(0)
print('Label $expected not found.'); sys.exit(1)
"
        ;;

    daemonset-toleration)
                ns="${1:?Missing namespace}"; ds="${2:?Missing daemonset}"; tol_key="${3:?Missing toleration key}"
                kubectl get daemonset "$ds" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
ds = json.load(sys.stdin)
tolerations = ds['spec']['template']['spec'].get('tolerations', [])
for t in tolerations:
    if t.get('key') == '$tol_key':
        print('Toleration for $tol_key found.'); sys.exit(0)
print('Toleration for $tol_key not found.'); sys.exit(1)
"
        ;;

    deploy-capabilities-drop)
                ns="${1:?Missing namespace}"; deploy="${2:?Missing deployment}"
                kubectl get deployment "$deploy" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
dep = json.load(sys.stdin)
containers = dep['spec']['template']['spec']['containers']
for c in containers:
    sc = c.get('securityContext', {})
    caps = sc.get('capabilities', {})
    drop = caps.get('drop', [])
    if 'ALL' not in drop:
        print(f'Container {c[\"name\"]} does not drop ALL. Got: {drop}'); sys.exit(1)
print('All containers drop ALL capabilities.')
"
        ;;

    deploy-container-security)
                ns="${1:?Missing namespace}"; deploy="${2:?Missing deployment}"
                field="${3:?Missing field}"; expected="${4:?Missing expected value}"
                kubectl get deployment "$deploy" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
dep = json.load(sys.stdin)
containers = dep['spec']['template']['spec']['containers']
for c in containers:
    sc = c.get('securityContext', {})
    val = sc.get('$field')
    if str(val) != '$expected':
        print(f'Container {c[\"name\"]} $field: expected $expected, got {val}'); sys.exit(1)
print('All containers have $field=$expected.')
"
        ;;

    deploy-pod-security)
                ns="${1:?Missing namespace}"; deploy="${2:?Missing deployment}"
                field="${3:?Missing field}"; expected="${4:?Missing expected value}"
                actual=$(kubectl get deployment "$deploy" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
dep = json.load(sys.stdin)
sc = dep['spec']['template']['spec'].get('securityContext', {})
print(sc.get('$field', ''))
")
                if [[ "$actual" == "$expected" ]]; then echo "Pod securityContext.$field = $expected."
                else echo "Pod securityContext.$field: expected '$expected', got '$actual'."; exit 1; fi
        ;;

    deployment-available)
        ns="${1:?Missing namespace}"
        name="${2:?Missing deployment name}"
        expected="${3:?Missing expected replicas}"
        available=$(kubectl get deployment "$name" -n "$ns" \
            -o jsonpath='{.status.availableReplicas}' 2>/dev/null || echo "0")
        available="${available:-0}"
        if [[ "$available" == "$expected" ]]; then
            echo "Deployment '$name' has $available/$expected available replicas."
        else
            echo "Deployment '$name' has $available/$expected available replicas."
            exit 1
        fi
        ;;

    deployment-env)
                ns="${1:?Missing namespace}"
                name="${2:?Missing deployment name}"
                env_name="${3:?Missing env var name}"
                expected_val="${4:?Missing expected value}"
                actual=$(kubectl get deployment "$name" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
dep = json.load(sys.stdin)
for c in dep['spec']['template']['spec']['containers']:
    for env in c.get('env', []):
        if env['name'] == '$env_name':
            print(env.get('value', ''))
            sys.exit(0)
print('')
")
                if [[ "$actual" == "$expected_val" ]]; then
                    echo "Env '$env_name' = '$expected_val'."
                else
                    echo "Env '$env_name' = '$actual', expected '$expected_val'."
                    exit 1
                fi
        ;;

    deployment-exists)
        ns="${1:?Missing namespace}"
        name="${2:?Missing deployment name}"
        if kubectl get deployment "$name" -n "$ns" &>/dev/null; then
            echo "Deployment '$name' exists."
        else
            echo "Deployment '$name' not found in namespace '$ns'."
            exit 1
        fi
        ;;

    deployment-has-affinity)
        ns="${1:?Missing namespace}"; deploy="${2:?Missing deployment}"
        affinity=$(kubectl get deployment "$deploy" -n "$ns" \
          -o jsonpath='{.spec.template.spec.affinity.nodeAffinity}' 2>/dev/null || echo "")
        if [[ -n "$affinity" ]]; then echo "Deployment $deploy has nodeAffinity."
        else echo "Deployment $deploy has no nodeAffinity."; exit 1; fi
        ;;

    deployment-has-resources)
                ns="${1:?Missing namespace}"; deploy="${2:?Missing deployment}"
                kubectl get deployment "$deploy" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
dep = json.load(sys.stdin)
c = dep['spec']['template']['spec']['containers'][0]
res = c.get('resources', {})
req = res.get('requests', {})
if not req.get('cpu'):
    print('No CPU request found.'); sys.exit(1)
print('Deployment has CPU resource requests.')
"
        ;;

    deployment-image)
        ns="${1:?Missing namespace}"
        name="${2:?Missing deployment name}"
        expected="${3:?Missing expected image}"
        actual=$(kubectl get deployment "$name" -n "$ns" \
            -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null)
        if [[ "$actual" == "$expected" ]]; then
            echo "Deployment '$name' uses image '$expected'."
        else
            echo "Deployment '$name' uses '$actual', expected '$expected'."
            exit 1
        fi
        ;;

    deployment-image-contains)
        ns="${1:?Missing namespace}"; deploy="${2:?Missing deployment}"; pattern="${3:?Missing pattern}"
        image=$(kubectl get deployment "$deploy" -n "$ns" \
          -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null || echo "")
        if echo "$image" | grep -q "$pattern"; then
            echo "Deployment $deploy image contains '$pattern': $image"
        else echo "Deployment $deploy image '$image' does not contain '$pattern'."; exit 1; fi
        ;;

    deployment-max-surge)
        ns="${1:?Missing namespace}"; deploy="${2:?Missing deployment}"; expected="${3:?Missing value}"
        actual=$(kubectl get deployment "$deploy" -n "$ns" -o jsonpath='{.spec.strategy.rollingUpdate.maxSurge}' 2>/dev/null || echo "")
        if [[ "$actual" == "$expected" ]]; then echo "maxSurge is $expected."
        else echo "maxSurge: expected $expected, got '$actual'."; exit 1; fi
        ;;

    deployment-max-unavailable)
        ns="${1:?Missing namespace}"; deploy="${2:?Missing deployment}"; expected="${3:?Missing value}"
        actual=$(kubectl get deployment "$deploy" -n "$ns" -o jsonpath='{.spec.strategy.rollingUpdate.maxUnavailable}' 2>/dev/null || echo "")
        if [[ "$actual" == "$expected" ]]; then echo "maxUnavailable is $expected."
        else echo "maxUnavailable: expected $expected, got '$actual'."; exit 1; fi
        ;;

    deployment-pod-label)
                ns="${1:?Missing namespace}"; deploy="${2:?Missing deployment}"; expected="${3:?Missing label}"
                key="${expected%%=*}"; value="${expected#*=}"
                kubectl get deployment "$deploy" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
dep = json.load(sys.stdin)
labels = dep['spec']['template']['metadata'].get('labels', {})
if labels.get('$key') == '$value':
    print('Label $expected found.'); sys.exit(0)
print('Label $expected not found. Got: ' + str(labels)); sys.exit(1)
"
        ;;

    deployment-ready)
        ns="${1:?Missing namespace}"; deploy="${2:?Missing deployment}"; expected="${3:?Missing count}"
        ready=$(kubectl get deployment "$deploy" -n "$ns" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
        if [[ "$ready" == "$expected" ]]; then echo "Deployment '$deploy' has $expected ready replicas."
        else echo "Deployment '$deploy' ready replicas: expected $expected, got $ready."; exit 1; fi
        ;;

    deployment-replicas)
        ns="${1:?Missing namespace}"; deploy="${2:?Missing deployment}"; expected="${3:?Missing replicas}"
        actual=$(kubectl get deployment "$deploy" -n "$ns" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")
        if [[ "$actual" == "$expected" ]]; then echo "Deployment '$deploy' has $expected replicas."
        else echo "Deployment '$deploy' replicas: expected $expected, got $actual."; exit 1; fi
        ;;

    deployment-revisions)
        ns="${1:?Missing namespace}"
        name="${2:?Missing deployment name}"
        min_revisions="${3:?Missing minimum revisions}"
        count=$(kubectl rollout history deployment/"$name" -n "$ns" 2>/dev/null \
            | grep -cE '^[0-9]+' || echo "0")
        if (( count >= min_revisions )); then
            echo "Deployment '$name' has $count revisions (>= $min_revisions)."
        else
            echo "Deployment '$name' has $count revisions, expected >= $min_revisions."
            exit 1
        fi
        ;;

    deployment-strategy)
        ns="${1:?Missing namespace}"; deploy="${2:?Missing deployment}"; expected="${3:?Missing strategy}"
        actual=$(kubectl get deployment "$deploy" -n "$ns" -o jsonpath='{.spec.strategy.type}' 2>/dev/null || echo "")
        if [[ "$actual" == "$expected" ]]; then echo "Strategy is '$expected'."
        else echo "Strategy: expected '$expected', got '$actual'."; exit 1; fi
        ;;

    dns-resolves)
        ns="${1:?Missing namespace}"
        pod="${2:?Missing pod name}"
        hostname="${3:?Missing hostname}"
        if kubectl exec "$pod" -n "$ns" -- nslookup "$hostname" &>/dev/null; then
            echo "DNS resolution for '$hostname' works."
        else
            echo "DNS resolution for '$hostname' failed."
            exit 1
        fi
        ;;

    endpoints-count-gte)
        ns="${1:?Missing namespace}"; svc="${2:?Missing service}"; min="${3:?Missing min}"
        count=$(kubectl get endpoints "$svc" -n "$ns" -o json 2>/dev/null | \
          python3 -c "import sys,json;d=json.load(sys.stdin);print(sum(len(s.get('addresses',[])) for s in d.get('subsets',[])))" 2>/dev/null || echo "0")
        if [[ "$count" -ge "$min" ]]; then echo "Service $svc has $count endpoints (>= $min)."
        else echo "Service $svc: $count endpoints, expected >= $min."; exit 1; fi
        ;;

    ephemeral-container-exists)
                ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"; ec="${3:?Missing ephemeral container}"
                kubectl get pod "$pod" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
pod = json.load(sys.stdin)
for c in pod['spec'].get('ephemeralContainers', []):
    if c['name'] == '$ec':
        print('Ephemeral container found.'); sys.exit(0)
print('Ephemeral container not found.'); sys.exit(1)
"
        ;;

    pod-file-contains)
        ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"
        path="${3:?Missing path}"; pattern="${4:?Missing pattern}"
        content=$(kubectl exec "$pod" -n "$ns" -- cat "$path" 2>/dev/null || echo "")
        if echo "$content" | grep -q "$pattern"; then
            echo "File '$path' contains '$pattern'."
        else echo "File '$path' does not contain '$pattern'."; exit 1; fi
        ;;

    file-contains-on-node)
        node="${1:?Missing node}"; filepath="${2:?Missing path}"; pattern="${3:?Missing pattern}"
        if ssh "$node" "sudo grep -q '$pattern' '$filepath'" 2>/dev/null; then
            echo "File '$filepath' on $node contains '$pattern'."
        else echo "File '$filepath' on $node does not contain '$pattern'."; exit 1; fi
        ;;

    file-content)
        ns="${1:?Missing namespace}"
        pod="${2:?Missing pod name}"
        path="${3:?Missing file path}"
        expected="${4:?Missing expected content}"
        actual=$(kubectl exec "$pod" -n "$ns" -- cat "$path" 2>/dev/null || echo "")
        actual=$(echo "$actual" | tr -d '[:space:]')
        expected_clean=$(echo "$expected" | tr -d '[:space:]')
        if [[ "$actual" == "$expected_clean" ]]; then
            echo "File '$path' contains expected content."
        else
            echo "File '$path': expected '$expected', got '$actual'."
            exit 1
        fi
        ;;

    pod-file-content)
        ns="${1:?Missing namespace}"
        pod="${2:?Missing pod name}"
        path="${3:?Missing file path}"
        expected="${4:?Missing expected content}"
        actual=$(kubectl exec "$pod" -n "$ns" -- cat "$path" 2>/dev/null || echo "")
        actual=$(echo "$actual" | tr -d '[:space:]')
        expected_clean=$(echo "$expected" | tr -d '[:space:]')
        if [[ "$actual" == "$expected_clean" ]]; then
            echo "File '$path' contains expected content."
        else
            echo "File '$path': expected '$expected', got '$actual'."
            exit 1
        fi
        ;;

    file-exists-in-pod)
        ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"; path="${3:?Missing path}"
        if kubectl exec "$pod" -n "$ns" -- test -f "$path" 2>/dev/null; then
            echo "File '$path' exists."
        else echo "File '$path' not found in pod."; exit 1; fi
        ;;

    file-exists-on-node)
        node="${1:?Missing node}"; filepath="${2:?Missing path}"
        if ssh "$node" "sudo test -f '$filepath'" 2>/dev/null; then
            echo "File '$filepath' exists on $node."
        else echo "File '$filepath' not found on $node."; exit 1; fi
        ;;

    file-has-content)
        ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"; container="${3:?Missing container}"; path="${4:?Missing path}"
        content=$(kubectl exec "$pod" -n "$ns" -c "$container" -- cat "$path" 2>/dev/null || echo "")
        if [[ -n "$content" ]]; then echo "File '$path' has content."
        else echo "File '$path' is empty or missing."; exit 1; fi
        ;;

    pod-file-has-content)
        ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"; container="${3:?Missing container}"; path="${4:?Missing path}"
        content=$(kubectl exec "$pod" -n "$ns" -c "$container" -- cat "$path" 2>/dev/null || echo "")
        if [[ -n "$content" ]]; then echo "File '$path' has content."
        else echo "File '$path' is empty or missing."; exit 1; fi
        ;;

    helm-release-exists)
        ns="${1:?Missing namespace}"; release="${2:?Missing release}"
        if helm status "$release" -n "$ns" &>/dev/null; then echo "Release '$release' exists."
        else echo "Release '$release' not found in namespace '$ns'."; exit 1; fi
        ;;

    helm-release-revision-gte)
        ns="${1:?Missing namespace}"; release="${2:?Missing release}"; min="${3:?Missing min}"
        rev=$(helm history "$release" -n "$ns" --max 100 -o json 2>/dev/null | python3 -c "import sys,json;print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
        if [[ "$rev" -ge "$min" ]]; then echo "Release '$release' has $rev revisions (>= $min)."
        else echo "Release '$release': $rev revisions, expected >= $min."; exit 1; fi
        ;;

    helm-release-status)
        ns="${1:?Missing namespace}"; release="${2:?Missing release}"; expected="${3:?Missing status}"
        actual=$(helm status "$release" -n "$ns" -o json 2>/dev/null | python3 -c "import sys,json;print(json.load(sys.stdin)['info']['status'])" 2>/dev/null || echo "")
        if [[ "$actual" == "$expected" ]]; then echo "Release '$release' status is $expected."
        else echo "Release '$release': expected status '$expected', got '$actual'."; exit 1; fi
        ;;

    hpa-exists)
        ns="${1:?Missing namespace}"; hpa="${2:?Missing hpa}"
        if kubectl get hpa "$hpa" -n "$ns" &>/dev/null; then echo "HPA '$hpa' exists."
        else echo "HPA '$hpa' not found."; exit 1; fi
        ;;

    hpa-min-max)
                ns="${1:?Missing namespace}"; hpa="${2:?Missing hpa}"
                min_r="${3:?Missing min}"; max_r="${4:?Missing max}"
                kubectl get hpa "$hpa" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
h = json.load(sys.stdin)
actual_min = h['spec'].get('minReplicas', 1)
actual_max = h['spec'].get('maxReplicas', 0)
if str(actual_min) == '$min_r' and str(actual_max) == '$max_r':
    print('HPA min=$min_r, max=$max_r.'); sys.exit(0)
print(f'HPA min={actual_min}, max={actual_max}, expected min=$min_r, max=$max_r.'); sys.exit(1)
"
        ;;

    hpa-target-ref)
                ns="${1:?Missing namespace}"; hpa="${2:?Missing hpa}"
                kind="${3:?Missing kind}"; name="${4:?Missing name}"
                kubectl get hpa "$hpa" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
h = json.load(sys.stdin)
ref = h['spec']['scaleTargetRef']
if ref.get('kind') == '$kind' and ref.get('name') == '$name':
    print('HPA targets $kind/$name.'); sys.exit(0)
print(f'HPA targets {ref.get(\"kind\")}/{ref.get(\"name\")}, expected $kind/$name.'); sys.exit(1)
"
        ;;

    http-reachable)
        ns="${1:?Missing namespace}"
        pod="${2:?Missing pod name}"
        hostname="${3:?Missing hostname}"
        if kubectl exec "$pod" -n "$ns" -- wget -q -O /dev/null \
            --timeout=5 "http://${hostname}" &>/dev/null; then
            echo "HTTP request to '$hostname' succeeded."
        else
            echo "HTTP request to '$hostname' failed."
            exit 1
        fi
        ;;

    httproute-path)
                ns="${1:?Missing namespace}"; route="${2:?Missing route}"; path="${3:?Missing path}"
                kubectl get httproute "$route" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
for rule in data.get('spec', {}).get('rules', []):
    for match in rule.get('matches', []):
        p = match.get('path', {})
        if p.get('value', '') == '$path':
            print('HTTPRoute has path $path.'); sys.exit(0)
print('Path $path not found.'); sys.exit(1)
"
        ;;

    ingress-class)
        ns="${1:?Missing namespace}"; ing="${2:?Missing ingress}"; expected="${3:?Missing class}"
        actual=$(kubectl get ingress "$ing" -n "$ns" -o jsonpath='{.spec.ingressClassName}' 2>/dev/null || echo "")
        if [[ "$actual" == "$expected" ]]; then echo "Ingress class is '$expected'."
        else echo "Ingress class: expected '$expected', got '$actual'."; exit 1; fi
        ;;

    ingress-path-backend)
                ns="${1:?Missing namespace}"; ing="${2:?Missing ingress}"
                path="${3:?Missing path}"; backend="${4:?Missing backend service}"
                kubectl get ingress "$ing" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
ing = json.load(sys.stdin)
for rule in ing['spec'].get('rules', []):
    for p in rule.get('http', {}).get('paths', []):
        if p.get('path') == '$path':
            svc_name = p.get('backend', {}).get('service', {}).get('name', '')
            if svc_name == '$backend':
                print('Path $path routes to $backend.'); sys.exit(0)
            else:
                print(f'Path $path routes to {svc_name}, expected $backend.'); sys.exit(1)
print('Path $path not found in Ingress.'); sys.exit(1)
"
        ;;

    ingress-tls-secret)
        ns="${1:?Missing namespace}"; ingress="${2:?Missing ingress}"; secret="${3:?Missing secret}"
        tls_secret=$(kubectl get ingress "$ingress" -n "$ns" -o json 2>/dev/null | \
          python3 -c "import sys,json;tls=json.load(sys.stdin).get('spec',{}).get('tls',[]);print(','.join(t.get('secretName','') for t in tls))" 2>/dev/null || echo "")
        if echo "$tls_secret" | grep -q "$secret"; then
            echo "Ingress $ingress uses TLS secret '$secret'."
        else echo "Ingress $ingress: TLS secret '$secret' not found."; exit 1; fi
        ;;

    init-container-exists)
                ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"; ic="${3:?Missing init container name}"
                result=$(kubectl get pod "$pod" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
pod = json.load(sys.stdin)
for c in pod['spec'].get('initContainers', []):
    if c['name'] == '$ic':
        print('found'); sys.exit(0)
print('not found'); sys.exit(1)
" 2>/dev/null || true)
                if [[ "$result" == "found" ]]; then echo "Init container '$ic' found."
                else echo "Init container '$ic' not found."; exit 1; fi
        ;;

    job-complete)
        ns="${1:?Missing namespace}"
        job="${2:?Missing job name}"

        if ! kubectl get job "$job" -n "$ns" &>/dev/null; then
            echo "Job '$job' not found."
            exit 1
        fi

        succeeded=$(kubectl get job "$job" -n "$ns" \
            -o jsonpath='{.status.succeeded}' 2>/dev/null || echo "0")
        succeeded="${succeeded:-0}"
        completions=$(kubectl get job "$job" -n "$ns" \
            -o jsonpath='{.spec.completions}' 2>/dev/null || echo "0")

        if [[ "$succeeded" == "$completions" ]]; then
            echo "Job '$job' completed ($succeeded/$completions)."
        else
            echo "Job '$job' not complete: $succeeded/$completions succeeded."
            exit 1
        fi
        ;;

    job-spec)
        ns="${1:?Missing namespace}"
        job="${2:?Missing job name}"
        expected_completions="${3:?Missing expected completions}"
        expected_parallelism="${4:?Missing expected parallelism}"

        if ! kubectl get job "$job" -n "$ns" &>/dev/null; then
            echo "Job '$job' not found in namespace '$ns'."
            exit 1
        fi

        completions=$(kubectl get job "$job" -n "$ns" \
            -o jsonpath='{.spec.completions}' 2>/dev/null)
        parallelism=$(kubectl get job "$job" -n "$ns" \
            -o jsonpath='{.spec.parallelism}' 2>/dev/null)

        errors=""
        if [[ "$completions" != "$expected_completions" ]]; then
            errors="completions=$completions (expected $expected_completions)"
        fi
        if [[ "$parallelism" != "$expected_parallelism" ]]; then
            errors="$errors parallelism=$parallelism (expected $expected_parallelism)"
        fi

        if [[ -z "$errors" ]]; then
            echo "Job '$job' has correct spec."
        else
            echo "Job '$job': $errors"
            exit 1
        fi
        ;;

    kubectl-works)
        if kubectl get nodes &>/dev/null; then echo "kubectl get nodes works."
        else echo "kubectl get nodes failed."; exit 1; fi
        ;;

    kubelet-active)
        node="${1:?Missing node}"
        state=$(ssh "$node" 'systemctl is-active kubelet' 2>/dev/null || echo "inactive")
        if [[ "$state" == "active" ]]; then echo "Kubelet is active on $node."
        else echo "Kubelet is $state on $node."; exit 1; fi
        ;;

    kubelet-config-value)
        key_path="${1:?Missing key}"; expected="${2:?Missing value}"
        actual=$(ssh master1 "sudo python3 -c \"
import yaml
with open('/var/lib/kubelet/config.yaml') as f:
    cfg = yaml.safe_load(f)
keys = '${key_path}'.split('.')
v = cfg
for k in keys:
    v = v.get(k, {})
print(str(v).lower())
\"" 2>/dev/null || echo "")
        if [[ "$actual" == "$expected" ]]; then
            echo "Kubelet config $key_path = $expected."
        else echo "Kubelet config $key_path: expected '$expected', got '$actual'."; exit 1; fi
        ;;

    namespace-exists)
        ns="${1:?Missing namespace name}"
        if kubectl get namespace "$ns" &>/dev/null; then
            echo "Namespace '$ns' exists."
        else
            echo "Namespace '$ns' not found."
            exit 1
        fi
        ;;

    namespace-label)
        ns="${1:?Missing namespace}"; label="${2:?Missing label}"
        key="${label%%=*}"; val="${label#*=}"
        # Handle keys with slashes by using JSON
        actual=$(kubectl get namespace "$ns" -o json 2>/dev/null | \
          python3 -c "import sys,json;labels=json.load(sys.stdin).get('metadata',{}).get('labels',{});print(labels.get('$key',''))" 2>/dev/null || echo "")
        if [[ "$actual" == "$val" ]]; then echo "Namespace '$ns' has label $label."
        else echo "Namespace '$ns': expected $key=$val, got '$actual'."; exit 1; fi
        ;;

    native-sidecar-exists)
                ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"; sc="${3:?Missing sidecar name}"
                kubectl get pod "$pod" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
pod = json.load(sys.stdin)
for c in pod['spec'].get('initContainers', []):
    if c['name'] == '$sc' and c.get('restartPolicy') == 'Always':
        print('Native sidecar found.'); sys.exit(0)
print('Native sidecar not found.'); sys.exit(1)
"
        ;;

    netpol-allows-egress-port)
                ns="${1:?Missing namespace}"; name="${2:?Missing netpol}"; port="${3:?Missing port}"
                kubectl get networkpolicy "$name" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
np = json.load(sys.stdin)
spec = np['spec']
egress = spec.get('egress', [])
if not egress:
    print('No egress rules found.'); sys.exit(1)
for rule in egress:
    for p in rule.get('ports', []):
        if str(p.get('port')) == '$port':
            print('Egress rule for port $port found.'); sys.exit(0)
print('No egress rule for port $port.'); sys.exit(1)
"
        ;;

    netpol-allows-ingress)
                ns="${1:?Missing namespace}"; name="${2:?Missing netpol}"
                pod_label="${3:?Missing pod selector}"; from_label="${4:?Missing from selector}"
                port="${5:?Missing port}"
                kubectl get networkpolicy "$name" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
np = json.load(sys.stdin)
spec = np['spec']
# Check podSelector targets the db
selector = spec.get('podSelector', {}).get('matchLabels', {})
key, val = '$pod_label'.split('=')
if selector.get(key) != val:
    print(f'podSelector does not target $pod_label.'); sys.exit(1)
# Check ingress rules
ingress = spec.get('ingress', [])
if not ingress:
    print('No ingress rules found.'); sys.exit(1)
found_from = False
found_port = False
for rule in ingress:
    for f in rule.get('from', []):
        fkey, fval = '$from_label'.split('=')
        ps = f.get('podSelector', {}).get('matchLabels', {})
        if ps.get(fkey) == fval:
            found_from = True
    for p in rule.get('ports', []):
        if str(p.get('port')) == '$port':
            found_port = True
if found_from and found_port:
    print('Ingress rule allowing $from_label -> $pod_label on port $port found.')
else:
    print(f'from={found_from}, port={found_port}'); sys.exit(1)
"
        ;;

    netpol-allows-ingress-any)
                ns="${1:?Missing namespace}"; name="${2:?Missing netpol}"
                pod_label="${3:?Missing pod selector}"; port="${4:?Missing port}"
                kubectl get networkpolicy "$name" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
np = json.load(sys.stdin)
spec = np['spec']
key, val = '$pod_label'.split('=')
selector = spec.get('podSelector', {}).get('matchLabels', {})
if selector.get(key) != val:
    print('podSelector does not target $pod_label.'); sys.exit(1)
ingress = spec.get('ingress', [])
if not ingress:
    print('No ingress rules found.'); sys.exit(1)
for rule in ingress:
    for p in rule.get('ports', []):
        if str(p.get('port')) == '$port':
            print('Ingress allow rule on port $port found.'); sys.exit(0)
print('No ingress rule for port $port.'); sys.exit(1)
"
        ;;

    netpol-deny-all)
                ns="${1:?Missing namespace}"; name="${2:?Missing netpol name}"; policy_type="${3:?Missing policy type}"
                kubectl get networkpolicy "$name" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
np = json.load(sys.stdin)
spec = np['spec']
# Empty podSelector means applies to all pods
selector = spec.get('podSelector', {})
match_labels = selector.get('matchLabels', {})
if match_labels:
    print('podSelector is not empty.'); sys.exit(1)
policy_types = spec.get('policyTypes', [])
if '$policy_type' not in policy_types:
    print('$policy_type not in policyTypes.'); sys.exit(1)
# For deny-all, there should be no ingress/egress rules
direction = '$policy_type'.lower()
rules = spec.get(direction, [])
if rules:
    print(f'Has {direction} rules, expected none for deny-all.'); sys.exit(1)
print('Default deny $policy_type policy verified.')
"
        ;;

    netpol-deny-egress)
                ns="${1:?Missing namespace}"; name="${2:?Missing netpol}"
                kubectl get networkpolicy "$name" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
np = json.load(sys.stdin)
spec = np['spec']
if 'Egress' not in spec.get('policyTypes', []):
    print('Egress not in policyTypes.'); sys.exit(1)
egress = spec.get('egress', [])
if not egress:
    print('Egress deny-all (no rules).'); sys.exit(0)
print('Has egress rules, not deny-all.'); sys.exit(1)
"
        ;;

    netpol-egress-to)
                ns="${1:?Missing namespace}"; name="${2:?Missing netpol}"
                to_label="${3:?Missing to selector}"; port="${4:?Missing port}"
                kubectl get networkpolicy "$name" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
np = json.load(sys.stdin)
tkey, tval = '$to_label'.split('=')
for rule in np['spec'].get('egress', []):
    found_to = any(
        t.get('podSelector', {}).get('matchLabels', {}).get(tkey) == tval
        for t in rule.get('to', [])
    )
    found_port = any(str(p.get('port')) == '$port' for p in rule.get('ports', []))
    if found_to and found_port:
        print('Egress rule found.'); sys.exit(0)
print('Expected egress rule not found.'); sys.exit(1)
"
        ;;

    netpol-exists)
        ns="${1:?Missing namespace}"
        name="${2:?Missing networkpolicy name}"
        if kubectl get networkpolicy "$name" -n "$ns" &>/dev/null; then
            echo "NetworkPolicy '$name' exists in namespace '$ns'."
        else
            echo "NetworkPolicy '$name' not found in namespace '$ns'."
            exit 1
        fi
        ;;

    netpol-ingress-from)
                ns="${1:?Missing namespace}"
                name="${2:?Missing networkpolicy name}"
                from_label="${3:?Missing from label (key=value)}"
                port="${4:?Missing port}"
                from_key="${from_label%%=*}"
                from_val="${from_label#*=}"

                result=$(kubectl get networkpolicy "$name" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
np = json.load(sys.stdin)
ingress = np.get('spec', {}).get('ingress', [])
for rule in ingress:
    froms = rule.get('from', [])
    ports = rule.get('ports', [])
    has_from = any(
        f.get('podSelector', {}).get('matchLabels', {}).get('$from_key') == '$from_val'
        for f in froms
    )
    has_port = any(
        str(p.get('port')) == '$port'
        for p in ports
    )
    if has_from and has_port:
        print('ok')
        sys.exit(0)
print('not found')
sys.exit(1)
")
                if [[ "$result" == "ok" ]]; then
                    echo "NetworkPolicy allows ingress from $from_label on port $port."
                else
                    echo "NetworkPolicy missing ingress rule: from $from_label port $port."
                    exit 1
                fi
        ;;

    netpol-pod-selector)
        ns="${1:?Missing namespace}"
        name="${2:?Missing networkpolicy name}"
        expected="${3:?Missing expected selector (key=value)}"
        key="${expected%%=*}"
        value="${expected#*=}"
        actual=$(kubectl get networkpolicy "$name" -n "$ns" \
            -o jsonpath="{.spec.podSelector.matchLabels.$key}" 2>/dev/null)
        if [[ "$actual" == "$value" ]]; then
            echo "NetworkPolicy '$name' selects $key=$value."
        else
            echo "NetworkPolicy '$name' podSelector.$key='$actual', expected '$value'."
            exit 1
        fi
        ;;

    node-has-label)
        node="${1:?Missing node}"; key="${2:?Missing key}"; value="${3:?Missing value}"
        actual=$(kubectl get node "$node" -o jsonpath="{.metadata.labels.$key}" 2>/dev/null || echo "")
        if [[ "$actual" == "$value" ]]; then echo "Node $node has label $key=$value."
        else echo "Node $node: expected label $key=$value, got '$actual'."; exit 1; fi
        ;;

    any-node-has-label)
        key="${1:?Missing key}"; value="${2:?Missing value}"
        found=$(kubectl get nodes -o jsonpath="{.items[*].metadata.labels.$key}" 2>/dev/null \
            | tr ' ' '\n' | grep -c "^${value}$" || echo "0")
        if [[ "$found" -gt 0 ]]; then echo "A node has label $key=$value."
        else echo "No node has label $key=$value."; exit 1; fi
        ;;

    any-worker-has-taint)
        taint="${1:?Missing taint}"
        result=$(kubectl get nodes -o json 2>/dev/null | python3 -c "
import sys, json
nodes = json.load(sys.stdin)['items']
taint_str = '$taint'
taint_key, sep, rest = taint_str.rpartition(':')
effect = rest
key, _, val = taint_key.partition('=')
for n in nodes:
    labels = n.get('metadata', {}).get('labels', {})
    if 'node-role.kubernetes.io/control-plane' in labels:
        continue
    for t in n.get('spec', {}).get('taints', []) or []:
        if t.get('key') == key and t.get('value', '') == val and t.get('effect') == effect:
            print('found'); sys.exit(0)
print('not found')
" 2>/dev/null || echo "not found")
        if [[ "$result" == "found" ]]; then echo "A worker node has taint $taint."
        else echo "No worker node has taint $taint."; exit 1; fi
        ;;

    node-has-taint)
        node="${1:?Missing node}"; taint="${2:?Missing taint}"
        taints=$(kubectl get node "$node" -o jsonpath='{.spec.taints[*]}' 2>/dev/null || echo "")
        if echo "$taints" | grep -q "${taint%%:*}"; then echo "Node $node has taint $taint."
        else echo "Node $node does not have taint $taint."; exit 1; fi
        ;;

    node-ready)
        node="${1:?Missing node}"
        status=$(kubectl get node "$node" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "")
        if [[ "$status" == "True" ]]; then echo "Node $node is Ready."
        else echo "Node $node is not Ready (status=$status)."; exit 1; fi
        ;;

    node-version)
        node="${1:?Missing node name}"; expected="${2:?Missing version prefix}"
        version=$(kubectl get node "$node" -o jsonpath='{.status.nodeInfo.kubeletVersion}' 2>/dev/null || echo "")
        if [[ "$version" == "$expected"* ]]; then
            echo "Node $node is running $version."
        else
            echo "Node $node: expected $expected*, got '$version'."; exit 1
        fi
        ;;

    pdb-exists)
        ns="${1:?Missing namespace}"; pdb="${2:?Missing pdb}"; min_avail="${3:?Missing minAvailable}"
        actual=$(kubectl get pdb "$pdb" -n "$ns" -o jsonpath='{.spec.minAvailable}' 2>/dev/null || echo "")
        if [[ "$actual" == "$min_avail" ]]; then echo "PDB '$pdb' minAvailable=$min_avail."
        else echo "PDB '$pdb' minAvailable: expected $min_avail, got '$actual'."; exit 1; fi
        ;;

    peerauth-mode)
        ns="${1:?Missing namespace}"; name="${2:?Missing name}"; expected="${3:?Missing mode}"
        actual=$(kubectl get peerauthentication.security.istio.io "$name" -n "$ns" \
          -o jsonpath='{.spec.mtls.mode}' 2>/dev/null || echo "")
        if [[ "$actual" == "$expected" ]]; then echo "PeerAuthentication $name mode = $expected."
        else echo "PeerAuthentication $name: expected mode '$expected', got '$actual'."; exit 1; fi
        ;;

    pod-annotation)
        ns="${1:?Missing namespace}"
        pod="${2:?Missing pod name}"
        expected="${3:?Missing expected annotation (key=value)}"
        key="${expected%%=*}"
        value="${expected#*=}"
        actual=$(kubectl get pod "$pod" -n "$ns" \
            -o jsonpath="{.metadata.annotations.$key}" 2>/dev/null)
        if [[ "$actual" != "$value" ]]; then
            echo "Annotation '$key': expected '$value', got '$actual'."
            exit 1
        fi
        echo "Annotation '$key' is correct."
        ;;

    pod-annotation-contains)
        ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"
        key_part="${3:?Missing key part}"; value_part="${4:?Missing value part}"
        annotations=$(kubectl get pod "$pod" -n "$ns" -o json 2>/dev/null | \
          python3 -c "import sys,json;a=json.load(sys.stdin).get('metadata',{}).get('annotations',{});print('\n'.join(f'{k}={v}' for k,v in a.items()))" 2>/dev/null || echo "")
        if echo "$annotations" | grep -q "$key_part" && echo "$annotations" | grep -q "$value_part"; then
            echo "Pod $pod has annotation containing '$key_part' with value containing '$value_part'."
        else echo "Pod $pod: missing annotation '$key_part' with '$value_part'."; exit 1; fi
        ;;

    pod-can-connect)
        ns="${1:?Missing namespace}"
        from_pod="${2:?Missing source pod}"
        to_pod="${3:?Missing target pod}"
        port="${4:?Missing port}"

        target_ip=$(kubectl get pod "$to_pod" -n "$ns" \
            -o jsonpath='{.status.podIP}' 2>/dev/null)
        if kubectl exec "$from_pod" -n "$ns" -- \
            sh -c "echo | nc -w 3 $target_ip $port" &>/dev/null; then
            echo "Pod '$from_pod' can connect to '$to_pod' on port $port."
        else
            echo "Pod '$from_pod' cannot connect to '$to_pod' on port $port."
            exit 1
        fi
        ;;

    pod-cannot-connect)
        ns="${1:?Missing namespace}"
        from_pod="${2:?Missing source pod}"
        to_pod="${3:?Missing target pod}"
        port="${4:?Missing port}"

        target_ip=$(kubectl get pod "$to_pod" -n "$ns" \
            -o jsonpath='{.status.podIP}' 2>/dev/null)
        if kubectl exec "$from_pod" -n "$ns" -- \
            sh -c "echo | nc -w 3 $target_ip $port" &>/dev/null; then
            echo "Pod '$from_pod' CAN still connect to '$to_pod' on port $port (should be blocked)."
            exit 1
        else
            echo "Pod '$from_pod' is correctly blocked from '$to_pod' on port $port."
        fi
        ;;

    pod-env-from-secret)
                ns="${1:?Missing namespace}"
                pod="${2:?Missing pod name}"
                env_name="${3:?Missing env var name}"
                secret="${4:?Missing secret name}"
                # Check if the pod has an env var sourced from the secret
                # Use || true to avoid set -e / pipefail aborting on sys.exit(1)
                result=$(kubectl get pod "$pod" -n "$ns" -o json 2>/dev/null | \
                    python3 -c "
import sys, json
pod = json.load(sys.stdin)
for container in pod['spec']['containers']:
    for env in container.get('env', []):
        ref = env.get('valueFrom', {}).get('secretKeyRef', {})
        if env.get('name') == '$env_name' and ref.get('name') == '$secret':
            print('found')
            sys.exit(0)
sys.exit(1)
        " 2>/dev/null || true)
                if [ "$result" != "found" ]; then
                    echo "Pod '$pod' does not have env '$env_name' from secret '$secret'."
                    exit 1
                fi
                echo "Pod '$pod' has env '$env_name' from secret '$secret'."
        ;;

    pod-env-from-source)
                ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"
                env_name="${3:?Missing env name}"; source_name="${4:?Missing source name}"
                # Check env var exists in the running pod
                actual=$(kubectl exec "$pod" -n "$ns" -- printenv "$env_name" 2>/dev/null || echo "")
                if [[ -z "$actual" ]]; then
                    echo "Env '$env_name' not set in pod."; exit 1
                fi
                # Verify source is the secret
                result=$(kubectl get pod "$pod" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
pod = json.load(sys.stdin)
for c in pod['spec']['containers']:
    for ef in c.get('envFrom', []):
        if ef.get('secretRef', {}).get('name') == '$source_name':
            print('envFrom'); sys.exit(0)
    for env in c.get('env', []):
        if env.get('name') == '$env_name':
            ref = env.get('valueFrom', {}).get('secretKeyRef', {})
            if ref.get('name') == '$source_name':
                print('valueFrom'); sys.exit(0)
print('not found'); sys.exit(1)
" 2>/dev/null || true)
                if [[ "$result" == "not found" || -z "$result" ]]; then
                    echo "Env '$env_name' not sourced from '$source_name'."; exit 1
                fi
                echo "Env '$env_name' sourced from '$source_name' ($result)."
        ;;

    pod-env-value)
        ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"
        env_name="${3:?Missing env name}"; expected="${4:?Missing expected value}"
        actual=$(kubectl exec "$pod" -n "$ns" -- printenv "$env_name" 2>/dev/null || echo "")
        if [[ "$actual" == "$expected" ]]; then echo "Env '$env_name' = '$expected'."
        else echo "Env '$env_name' = '$actual', expected '$expected'."; exit 1; fi
        ;;

    pod-envfrom-configmap)
        ns="${1:?Missing namespace}"
        pod="${2:?Missing pod name}"
        cm="${3:?Missing configmap name}"
        result=$(kubectl get pod "$pod" -n "$ns" -o jsonpath='{.spec.containers[0].envFrom[*].configMapRef.name}' 2>/dev/null)
        if [[ "$result" != *"$cm"* ]]; then
            echo "Pod '$pod' does not use envFrom with ConfigMap '$cm'."
            exit 1
        fi
        echo "Pod '$pod' uses envFrom with ConfigMap '$cm'."
        ;;

    pod-exists)
        ns="${1:?Missing namespace}"
        pod="${2:?Missing pod name}"
        kubectl get pod "$pod" -n "$ns" &>/dev/null
        echo "Pod '$pod' exists in namespace '$ns'."
        ;;

    pod-exists-pattern)
        ns="${1:?Missing namespace}"; pattern="${2:?Missing pattern}"
        if kubectl get pod "$pattern" -n "$ns" &>/dev/null; then
            echo "Pod '$pattern' exists in namespace '$ns'."
        else echo "Pod '$pattern' not found in namespace '$ns'."; exit 1; fi
        ;;

    pod-image)
        ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"; expected="${3:?Missing image}"
        actual=$(kubectl get pod "$pod" -n "$ns" -o jsonpath='{.spec.containers[0].image}' 2>/dev/null || echo "")
        if [[ "$actual" == "$expected" ]]; then echo "Pod uses $expected."
        else echo "Pod image: expected '$expected', got '$actual'."; exit 1; fi
        ;;

    pod-image-contains)
        ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"; substr="${3:?Missing substring}"
        actual=$(kubectl get pod "$pod" -n "$ns" -o jsonpath='{.spec.containers[0].image}' 2>/dev/null || echo "")
        if [[ "$actual" == *"$substr"* ]]; then echo "Pod $pod image contains '$substr': $actual."
        else echo "Pod $pod image '$actual' does not contain '$substr'."; exit 1; fi
        ;;

    pod-labels)
        ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"; expected="${3:?Missing labels}"
        IFS=',' read -ra LABELS <<< "$expected"
        for label in "${LABELS[@]}"; do
            key="${label%%=*}"; value="${label#*=}"
            actual=$(kubectl get pod "$pod" -n "$ns" -o jsonpath="{.metadata.labels.$key}" 2>/dev/null)
            if [[ "$actual" != "$value" ]]; then
                echo "Pod '$pod' label $key: expected '$value', got '$actual'."; exit 1
            fi
        done
        echo "All expected labels found."
        ;;

    pod-memory-limit-min)
                ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"; min_mi="${3:?Missing min MiB}"
                kubectl get pod "$pod" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
pod = json.load(sys.stdin)
c = pod['spec']['containers'][0]
limit = c.get('resources', {}).get('limits', {}).get('memory', '0')
# Parse memory value to MiB
val = limit.rstrip('MiGiKi')
unit = limit[len(val):]
val = int(val)
if 'Gi' in unit:
    mib = val * 1024
elif 'Mi' in unit:
    mib = val
elif 'Ki' in unit:
    mib = val // 1024
else:
    mib = val // (1024*1024)
if mib >= $min_mi:
    print(f'Memory limit {limit} >= ${min_mi}Mi.'); sys.exit(0)
print(f'Memory limit {limit} < ${min_mi}Mi.'); sys.exit(1)
"
        ;;

    pod-not-crashloop)
        ns="${1:?Missing namespace}"
        selector="${2:?Missing label selector}"
        crashloop=$(kubectl get pods -n "$ns" -l "$selector" --no-headers 2>/dev/null \
            | awk '$3 ~ /CrashLoop|Error/ {print $1}' || true)
        if [[ -z "$crashloop" ]]; then
            echo "No pods in CrashLoopBackOff."
        else
            echo "Pods still in CrashLoopBackOff: $crashloop"
            exit 1
        fi
        ;;

    pod-not-on-node)
        ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"; node="${3:?Missing node}"
        actual=$(kubectl get pod "$pod" -n "$ns" -o jsonpath='{.spec.nodeName}' 2>/dev/null || echo "")
        if [[ "$actual" != "$node" ]]; then echo "Pod $pod is NOT on node $node (on $actual)."
        else echo "Pod $pod is on node $node but should not be."; exit 1; fi
        ;;

    pod-on-node)
        ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"; node="${3:?Missing node}"
        actual=$(kubectl get pod "$pod" -n "$ns" -o jsonpath='{.spec.nodeName}' 2>/dev/null || echo "")
        if [[ "$actual" == "$node" ]]; then echo "Pod $pod is on node $node."
        else echo "Pod $pod: expected node '$node', got '$actual'."; exit 1; fi
        ;;

    pod-on-any-worker)
        ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"
        actual=$(kubectl get pod "$pod" -n "$ns" -o jsonpath='{.spec.nodeName}' 2>/dev/null || echo "")
        is_cp=$(kubectl get node "$actual" -o json 2>/dev/null \
            | python3 -c "import sys,json; n=json.load(sys.stdin); print('true' if 'node-role.kubernetes.io/control-plane' in n.get('metadata',{}).get('labels',{}) else 'false')" \
            2>/dev/null || echo "false")
        if [[ "$is_cp" == "false" ]]; then echo "Pod $pod is on worker node $actual."
        else echo "Pod $pod is on control-plane node '$actual', not a worker."; exit 1; fi
        ;;

    pod-not-on-any-worker)
        ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"
        actual=$(kubectl get pod "$pod" -n "$ns" -o jsonpath='{.spec.nodeName}' 2>/dev/null || echo "")
        is_cp=$(kubectl get node "$actual" -o json 2>/dev/null \
            | python3 -c "import sys,json; n=json.load(sys.stdin); print('true' if 'node-role.kubernetes.io/control-plane' in n.get('metadata',{}).get('labels',{}) else 'false')" \
            2>/dev/null || echo "false")
        if [[ "$is_cp" == "true" ]]; then echo "Pod $pod is NOT on a worker node (on $actual)."
        else echo "Pod $pod is on worker node $actual but should not be."; exit 1; fi
        ;;

    pod-prefix-running)
        ns="${1:?Missing namespace}"; prefix="${2:?Missing prefix}"
        pods=$(kubectl get pods -n "$ns" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)
        for p in $pods; do
            if [[ "$p" == "$prefix"* ]]; then
                phase=$(kubectl get pod "$p" -n "$ns" -o jsonpath='{.status.phase}' 2>/dev/null || echo "")
                if [[ "$phase" == "Running" ]]; then
                    echo "Pod '$p' with prefix '$prefix' is Running."
                    exit 0
                fi
            fi
        done
        echo "No running pod with prefix '$prefix' found."; exit 1
        ;;

    pod-pvc-mount)
                ns="${1:?Missing namespace}"
                pod="${2:?Missing pod name}"
                pvc="${3:?Missing PVC name}"
                mount_path="${4:?Missing mount path}"

                result=$(kubectl get pod "$pod" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
pod = json.load(sys.stdin)
spec = pod['spec']
pvc_vol = None
for v in spec.get('volumes', []):
    pvc_claim = v.get('persistentVolumeClaim', {})
    if pvc_claim.get('claimName') == '$pvc':
        pvc_vol = v['name']
        break
if not pvc_vol:
    print('PVC $pvc not found in pod volumes')
    sys.exit(1)
for c in spec['containers']:
    for vm in c.get('volumeMounts', []):
        if vm['name'] == pvc_vol and vm['mountPath'] == '$mount_path':
            print('ok')
            sys.exit(0)
print(f'Volume {pvc_vol} not mounted at \$mount_path')
sys.exit(1)
")
                if [[ "$result" == "ok" ]]; then
                    echo "Pod '$pod' mounts PVC '$pvc' at $mount_path."
                else
                    echo "$result"
                    exit 1
                fi
        ;;

    pod-ready)
        ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"
        ready=$(kubectl get pod "$pod" -n "$ns" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "")
        if [[ "$ready" == "True" ]]; then echo "Pod '$pod' is Ready."
        else echo "Pod '$pod' is not Ready."; exit 1; fi
        ;;

    pod-resource)
        ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"
        req_or_lim="${3:?Missing requests|limits}"; resource="${4:?Missing cpu|memory}"; expected="${5:?Missing value}"
        actual=$(kubectl get pod "$pod" -n "$ns" \
          -o jsonpath="{.spec.containers[0].resources.${req_or_lim}.${resource}}" 2>/dev/null || echo "")
        if [[ "$actual" == "$expected" ]]; then echo "Pod $pod $req_or_lim.$resource = $expected."
        else echo "Pod $pod $req_or_lim.$resource: expected '$expected', got '$actual'."; exit 1; fi
        ;;

    pod-restart-count)
        ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"; expected="${3:?Missing count}"
        actual=$(kubectl get pod "$pod" -n "$ns" \
          -o jsonpath='{.status.containerStatuses[0].restartCount}' 2>/dev/null || echo "-1")
        if [[ "$actual" == "$expected" ]]; then echo "Pod $pod restart count = $expected."
        else echo "Pod $pod restart count: expected $expected, got $actual."; exit 1; fi
        ;;

    pod-running)
        ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"
        phase=$(kubectl get pod "$pod" -n "$ns" -o jsonpath='{.status.phase}' 2>/dev/null || echo "")
        if [[ "$phase" == "Running" ]]; then echo "Pod '$pod' is Running."
        else echo "Pod '$pod' phase is '$phase', expected Running."; exit 1; fi
        ;;

    pod-running-pattern)
        ns="${1:?Missing namespace}"; pattern="${2:?Missing pattern}"
        phase=$(kubectl get pod "$pattern" -n "$ns" -o jsonpath='{.status.phase}' 2>/dev/null || echo "")
        if [[ "$phase" == "Running" ]]; then echo "Pod '$pattern' is Running."
        else echo "Pod '$pattern': expected Running, got '$phase'."; exit 1; fi
        ;;

    pod-runtimeclass)
        ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"; expected="${3:?Missing class}"
        actual=$(kubectl get pod "$pod" -n "$ns" -o jsonpath='{.spec.runtimeClassName}' 2>/dev/null || echo "")
        if [[ "$actual" == "$expected" ]]; then
            echo "Pod $pod runtimeClassName = $expected."
        else echo "Pod $pod: expected runtimeClassName '$expected', got '$actual'."; exit 1; fi
        ;;

    pod-seccomp-type)
        ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"; expected="${3:?Missing type}"
        actual=$(kubectl get pod "$pod" -n "$ns" \
          -o jsonpath='{.spec.securityContext.seccompProfile.type}' 2>/dev/null || echo "")
        if [[ "$actual" == "$expected" ]]; then
            echo "Pod $pod seccomp type = $expected."
        else echo "Pod $pod seccomp type: expected '$expected', got '$actual'."; exit 1; fi
        ;;

    pod-security-context)
                ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"
                result=$(kubectl get pod "$pod" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
p = json.load(sys.stdin)
sc = p['spec'].get('securityContext', {})
csc = p['spec']['containers'][0].get('securityContext', {})
errors = []
if not sc.get('runAsNonRoot'):
    errors.append('runAsNonRoot not set')
if csc.get('allowPrivilegeEscalation', True):
    errors.append('allowPrivilegeEscalation not false')
caps = csc.get('capabilities', {}).get('drop', [])
if 'ALL' not in [c.upper() for c in caps]:
    errors.append('capabilities.drop ALL missing')
if errors:
    print('FAIL: ' + '; '.join(errors))
else:
    print('OK')
" 2>/dev/null || echo "FAIL: cannot parse")
                if [[ "$result" == "OK" ]]; then echo "Pod $pod security context is compliant."
                else echo "$result"; exit 1; fi
        ;;

    pod-security-field)
        ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"
        field="${3:?Missing field}"; expected="${4:?Missing expected value}"
        actual=$(kubectl get pod "$pod" -n "$ns" -o jsonpath="{.spec.securityContext.$field}" 2>/dev/null || echo "")
        if [[ "$actual" == "$expected" ]]; then echo "Pod securityContext.$field = $expected."
        else echo "Pod securityContext.$field: expected '$expected', got '$actual'."; exit 1; fi
        ;;

    pods-running)
        ns="${1:?Missing namespace}"
        selector="${2:?Missing label selector}"
        total=$(kubectl get pods -n "$ns" -l "$selector" --no-headers 2>/dev/null | wc -l)
        if (( total == 0 )); then
            echo "No pods found with selector '$selector' in '$ns'."
            exit 1
        fi
        not_running=$(kubectl get pods -n "$ns" -l "$selector" --no-headers 2>/dev/null \
            | awk '$3 != "Running" {print $1, $3}' || true)
        if [[ -z "$not_running" ]]; then
            echo "All $total pods with selector '$selector' are Running."
        else
            echo "Some pods are not Running:"
            echo "$not_running"
            exit 1
        fi
        ;;

    privileged-rejected)
        ns="${1:?Missing namespace}"
        # Try to create a privileged pod — should fail
        output=$(kubectl run psa-test-priv --image=nginx:1.27 -n "$ns" \
            --overrides='{
              "spec":{
                "containers":[{
                  "name":"priv",
                  "image":"nginx:1.27",
                  "securityContext":{"privileged":true}
                }]
              }
            }' 2>&1 || true)
        # Clean up in case it somehow got created
        kubectl delete pod psa-test-priv -n "$ns" --ignore-not-found &>/dev/null || true
        if echo "$output" | grep -qi "forbidden\|violat"; then
            echo "Privileged pods are correctly rejected."
        else
            echo "Privileged pod was NOT rejected. Output: $output"
            exit 1
        fi
        ;;

    probe-exists)
                ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"
                probe_type="${3:?Missing probe type}"; probe_action="${4:?Missing probe action}"
                kubectl get pod "$pod" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
pod = json.load(sys.stdin)
for container in pod['spec']['containers']:
    probe = container.get('$probe_type')
    if probe and '$probe_action' in probe:
        print('$probe_type with $probe_action found.'); sys.exit(0)
print('$probe_type with $probe_action not found.'); sys.exit(1)
" 2>/dev/null
        ;;

    pv-exists)
        pv="${1:?Missing PV name}"
        expected_cap="${2:?Missing expected capacity}"
        if ! kubectl get pv "$pv" &>/dev/null; then
            echo "PersistentVolume '$pv' not found."
            exit 1
        fi
        actual=$(kubectl get pv "$pv" -o jsonpath='{.spec.capacity.storage}' 2>/dev/null)
        if [[ "$actual" == "$expected_cap" ]]; then
            echo "PV '$pv' exists with capacity $actual."
        else
            echo "PV '$pv' has capacity '$actual', expected '$expected_cap'."
            exit 1
        fi
        ;;

    pvc-bound)
        ns="${1:?Missing namespace}"
        pvc="${2:?Missing PVC name}"
        if ! kubectl get pvc "$pvc" -n "$ns" &>/dev/null; then
            echo "PVC '$pvc' not found in namespace '$ns'."
            exit 1
        fi
        phase=$(kubectl get pvc "$pvc" -n "$ns" -o jsonpath='{.status.phase}' 2>/dev/null)
        if [[ "$phase" == "Bound" ]]; then
            echo "PVC '$pvc' is Bound."
        else
            echo "PVC '$pvc' phase is '$phase', expected 'Bound'."
            exit 1
        fi
        ;;

    resource-absent)
        kind="${1:?Missing kind}"; name="${2:?Missing name}"
        if kubectl get "$kind" "$name" &>/dev/null 2>&1; then
            echo "$kind '$name' still exists."; exit 1
        else echo "$kind '$name' has been deleted."; fi
        ;;

    resource-exists)
        kind="${1:?Missing kind}"; ns="${2:?Missing namespace}"; name="${3:?Missing name}"
        if kubectl get "$kind" "$name" -n "$ns" &>/dev/null; then
            echo "$kind '$name' exists in namespace '$ns'."
        else echo "$kind '$name' not found in namespace '$ns'."; exit 1; fi
        ;;

    role-has-verb)
                ns="${1:?Missing namespace}"; role="${2:?Missing role}"; verb="${3:?Missing verb}"
                kubectl get role "$role" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
role = json.load(sys.stdin)
for rule in role.get('rules', []):
    if '$verb' in rule.get('verbs', []):
        print('Role has verb $verb.'); sys.exit(0)
print('Verb $verb not found in role.'); sys.exit(1)
" 2>/dev/null
        ;;

    role-rules)
                ns="${1:?Missing namespace}"
                role="${2:?Missing role name}"
                expected_resource="${3:?Missing resource}"
                expected_verbs="${4:?Missing verbs (comma-separated)}"

                if ! kubectl get role "$role" -n "$ns" &>/dev/null; then
                    echo "Role '$role' not found in namespace '$ns'."
                    exit 1
                fi

                IFS=',' read -ra VERBS <<< "$expected_verbs"
                json=$(kubectl get role "$role" -n "$ns" -o json)

                for verb in "${VERBS[@]}"; do
                    found=$(echo "$json" | python3 -c "
import sys, json
role = json.load(sys.stdin)
for rule in role.get('rules', []):
    if '$expected_resource' in rule.get('resources', []) and '$verb' in rule.get('verbs', []):
        print('yes'); sys.exit(0)
print('no')
" 2>/dev/null || true)
                    if [[ "$found" != "yes" ]]; then
                        echo "Role '$role' missing verb '$verb' on resource '$expected_resource'."
                        exit 1
                    fi
                done
                echo "Role '$role' has correct rules."
        ;;

    rolebinding-sa-subject)
                ns="${1:?Missing namespace}"; rb="${2:?Missing rolebinding}"; sa="${3:?Missing sa}"
                kubectl get rolebinding "$rb" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
rb = json.load(sys.stdin)
for s in rb.get('subjects', []):
    if s.get('kind') == 'ServiceAccount' and s.get('name') == '$sa':
        print('ServiceAccount $sa found.'); sys.exit(0)
print('ServiceAccount $sa not found.'); sys.exit(1)
"
        ;;

    rolebinding-subject)
                ns="${1:?Missing namespace}"
                rb="${2:?Missing rolebinding name}"
                role="${3:?Missing role name}"
                subject="${4:?Missing subject name}"

                if ! kubectl get rolebinding "$rb" -n "$ns" &>/dev/null; then
                    echo "RoleBinding '$rb' not found in namespace '$ns'."
                    exit 1
                fi

                role_ref=$(kubectl get rolebinding "$rb" -n "$ns" \
                    -o jsonpath='{.roleRef.name}' 2>/dev/null)
                if [[ "$role_ref" != "$role" ]]; then
                    echo "RoleBinding '$rb' references role '$role_ref', expected '$role'."
                    exit 1
                fi

                subject_found=$(kubectl get rolebinding "$rb" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
rb = json.load(sys.stdin)
for s in rb.get('subjects', []):
    if s.get('name') == '$subject':
        print('yes'); sys.exit(0)
print('no')
" 2>/dev/null || true)
                if [[ "$subject_found" != "yes" ]]; then
                    echo "RoleBinding '$rb' does not bind to subject '$subject'."
                    exit 1
                fi
                echo "RoleBinding '$rb' correctly binds '$role' to '$subject'."
        ;;

    runtimeclass-handler)
        name="${1:?Missing name}"; expected="${2:?Missing handler}"
        actual=$(kubectl get runtimeclass "$name" -o jsonpath='{.handler}' 2>/dev/null || echo "")
        if [[ "$actual" == "$expected" ]]; then
            echo "RuntimeClass '$name' handler = $expected."
        else echo "RuntimeClass '$name': expected handler '$expected', got '$actual'."; exit 1; fi
        ;;

    sa-can-i)
        ns="${1:?Missing namespace}"; sa="${2:?Missing sa}"
        verb="${3:?Missing verb}"; resource="${4:?Missing resource}"; expected="${5:?Missing yes/no}"
        result=$(kubectl auth can-i "$verb" "$resource" -n "$ns" \
          --as="system:serviceaccount:$ns:$sa" 2>/dev/null || echo "no")
        if [[ "$result" == "$expected" ]]; then echo "SA $sa can-i $verb $resource = $expected."
        else echo "SA $sa can-i $verb $resource: expected '$expected', got '$result'."; exit 1; fi
        ;;

    sa-exists)
        ns="${1:?Missing namespace}"
        sa="${2:?Missing serviceaccount name}"
        if kubectl get serviceaccount "$sa" -n "$ns" &>/dev/null; then
            echo "ServiceAccount '$sa' exists in namespace '$ns'."
        else
            echo "ServiceAccount '$sa' not found in namespace '$ns'."
            exit 1
        fi
        ;;

    sa-no-automount)
        ns="${1:?Missing namespace}"; sa="${2:?Missing sa}"
        val=$(kubectl get serviceaccount "$sa" -n "$ns" \
          -o jsonpath='{.automountServiceAccountToken}' 2>/dev/null || echo "")
        if [[ "$val" == "false" ]]; then echo "SA $sa automountServiceAccountToken = false."
        else echo "SA $sa automountServiceAccountToken: '$val' (expected false)."; exit 1; fi
        ;;

    secret-key-exists)
        ns="${1:?Missing namespace}"
        secret="${2:?Missing secret name}"
        key="${3:?Missing key name}"
        kubectl get secret "$secret" -n "$ns" -o jsonpath="{.data.$key}" &>/dev/null
        actual=$(kubectl get secret "$secret" -n "$ns" -o jsonpath="{.data.$key}" 2>/dev/null)
        if [ -z "$actual" ]; then
            echo "Secret '$secret' does not have key '$key'."
            exit 1
        fi
        echo "Secret '$secret' has key '$key'."
        ;;

    secret-keys)
        ns="${1:?Missing namespace}"; secret="${2:?Missing secret}"; keys="${3:?Missing keys}"
        IFS=',' read -ra KEYS <<< "$keys"
        for key in "${KEYS[@]}"; do
            val=$(kubectl get secret "$secret" -n "$ns" -o jsonpath="{.data.$key}" 2>/dev/null)
            if [[ -z "$val" ]]; then
                echo "Secret '$secret' missing key '$key'."; exit 1
            fi
        done
        echo "Secret '$secret' has all expected keys."
        ;;

    secret-type)
        ns="${1:?Missing namespace}"; name="${2:?Missing secret}"; expected="${3:?Missing type}"
        actual=$(kubectl get secret "$name" -n "$ns" -o jsonpath='{.type}' 2>/dev/null || echo "")
        if [[ "$actual" == "$expected" ]]; then echo "Secret $name type = $expected."
        else echo "Secret $name: expected type '$expected', got '$actual'."; exit 1; fi
        ;;

    node-service-active)
        node="${1:?Missing node}"; service="${2:?Missing service}"
        if ssh "$node" "systemctl is-active '$service'" 2>/dev/null | grep -q "active"; then
            echo "Service '$service' is active on $node."
        else echo "Service '$service' not active on $node."; exit 1; fi
        ;;

    service-exists)
        ns="${1:?Missing namespace}"; svc="${2:?Missing service}"
        if kubectl get service "$svc" -n "$ns" &>/dev/null; then echo "Service '$svc' exists."
        else echo "Service '$svc' not found."; exit 1; fi
        ;;

    service-has-endpoints)
                ns="${1:?Missing namespace}"; svc="${2:?Missing service}"
                ep_count=$(kubectl get endpoints "$svc" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
ep = json.load(sys.stdin)
count = sum(len(s.get('addresses', [])) for s in ep.get('subsets', []))
print(count)
" 2>/dev/null || echo 0)
                ep_count="${ep_count:-0}"
                if (( ep_count > 0 )); then echo "Service '$svc' has $ep_count endpoint(s)."
                else echo "Service '$svc' has no endpoints."; exit 1; fi
        ;;

    service-port)
        ns="${1:?Missing namespace}"
        svc="${2:?Missing service name}"
        expected="${3:?Missing expected port}"
        actual=$(kubectl get service "$svc" -n "$ns" -o jsonpath='{.spec.ports[0].port}' 2>/dev/null)
        if [ "$actual" != "$expected" ]; then
            echo "Service '$svc' port is $actual, expected $expected."
            exit 1
        fi
        echo "Service '$svc' exposes port $expected."
        ;;

    service-selector)
        ns="${1:?Missing namespace}"; svc="${2:?Missing service}"; expected="${3:?Missing selector}"
        key="${expected%%=*}"; value="${expected#*=}"
        actual=$(kubectl get service "$svc" -n "$ns" -o jsonpath="{.spec.selector.$key}" 2>/dev/null || echo "")
        if [[ "$actual" == "$value" ]]; then echo "Service selector $expected correct."
        else echo "Service selector $key: expected '$value', got '$actual'."; exit 1; fi
        ;;

    service-target-port)
                ns="${1:?Missing namespace}"; svc="${2:?Missing service}"; expected="${3:?Missing port}"
                kubectl get service "$svc" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
svc = json.load(sys.stdin)
for p in svc['spec'].get('ports', []):
    tp = str(p.get('targetPort', ''))
    if tp == '$expected':
        print('Target port $expected correct.'); sys.exit(0)
print('Target port $expected not found.'); sys.exit(1)
"
        ;;

    snapshot-exists)
        _ssh_master() { ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
            -i "${KXL_SSH_KEY}" "dsox@${KXL_MASTER1_IP}" "sudo $*" 2>/dev/null; }
        if [[ -n "${KXL_MASTER1_IP:-}" && -n "${KXL_SSH_KEY:-}" ]]; then
            size=$(_ssh_master stat -c%s /tmp/etcd-snapshot.db 2>/dev/null || echo 0)
            if (( size > 0 )); then
                echo "Snapshot /tmp/etcd-snapshot.db exists (${size} bytes)."
            else
                echo "Snapshot /tmp/etcd-snapshot.db not found."
                exit 1
            fi
        elif [[ -f /tmp/etcd-snapshot.db ]]; then
            size=$(stat -c%s /tmp/etcd-snapshot.db 2>/dev/null || echo 0)
            if (( size > 0 )); then
                echo "Snapshot /tmp/etcd-snapshot.db exists (${size} bytes)."
            else
                echo "Snapshot /tmp/etcd-snapshot.db exists but is empty."
                exit 1
            fi
        else
            echo "Snapshot /tmp/etcd-snapshot.db not found."
            exit 1
        fi
        ;;

    snapshot-valid)
        _ssh_master() { ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
            -i "${KXL_SSH_KEY}" "dsox@${KXL_MASTER1_IP}" "sudo $*" 2>/dev/null; }
        if [[ -n "${KXL_MASTER1_IP:-}" && -n "${KXL_SSH_KEY:-}" ]]; then
            if _ssh_master ETCDCTL_API=3 etcdctl snapshot status /tmp/etcd-snapshot.db; then
                echo "Snapshot is valid."
            else
                echo "Snapshot /tmp/etcd-snapshot.db not found."
                exit 1
            fi
        elif [[ ! -f /tmp/etcd-snapshot.db ]]; then
            echo "Snapshot /tmp/etcd-snapshot.db not found."
            exit 1
        elif ETCDCTL_API=3 etcdctl snapshot status /tmp/etcd-snapshot.db &>/dev/null; then
            echo "Snapshot is valid."
        else
            echo "Snapshot is not a valid etcd snapshot."
            exit 1
        fi
        ;;

    volume-emptydir)
                ns="${1:?Missing namespace}"; pod="${2:?Missing pod}"; vol="${3:?Missing volume name}"
                kubectl get pod "$pod" -n "$ns" -o json 2>/dev/null | python3 -c "
import sys, json
pod = json.load(sys.stdin)
for v in pod['spec'].get('volumes', []):
    if v['name'] == '$vol' and 'emptyDir' in v:
        print('emptyDir volume found.'); sys.exit(0)
print('emptyDir volume not found.'); sys.exit(1)
"
        ;;

    *) return 2 ;;
    esac
}
