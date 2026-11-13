#!/usr/bin/env bash
# Pose la situation du lab k8s-prioriser-et-preempter sur le cluster kind multi.
#
# Sur kind, chaque nœud annonce TOUS les CPU de l'hôte : une valeur fixe de
# requests remplirait un nœud sur une machine et pas sur une autre. Le
# remplissage se calcule donc ici, sur l'allocatable réel du worker multi-worker
# moins ce que ses Pods demandent déjà :
#
#   libre = allocatable - déjà demandé ;  part = libre / 4 (arrondi en dessous)
#
# Quatre réplicas de remplissage demandent chacun « part » : il reste moins
# d'une part de libre, et le Pod urgent, qui demande une part, ne tient que si
# un Pod de remplissage s'en va.
#
# Rejouable : le namespace est attendu s'il se termine, et les deux
# PriorityClass d'un passage précédent, basse et haute, objets du cluster, sont
# retirées. Aucune autre.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
NOEUD=multi-worker
NS=ordonnancement
BUSYBOX="busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"

# Seules les deux classes du lab, nommément : une PriorityClass posée par un
# autre lab ou par l'apprenant hors de ce lab n'a pas à disparaître (audit du
# 2026-11-13).
kubectl delete priorityclass basse haute --ignore-not-found
if [[ "$(kubectl get namespace "$NS" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete "namespace/$NS" --timeout=180s
fi
kubectl delete namespace "$NS" --ignore-not-found --wait=true --timeout=180s
kubectl create namespace "$NS"

PART=$(kubectl get node "$NOEUD" -o json | python3 -c '
import json, subprocess, sys
def milli(v):
    v = str(v)
    return int(float(v[:-1])) if v.endswith("m") else int(float(v) * 1000)
noeud = json.load(sys.stdin)
alloue = milli(noeud["status"]["allocatable"]["cpu"])
pods = json.loads(subprocess.run(["kubectl", "get", "pods", "-A", "-o", "json",
    "--field-selector", "spec.nodeName=" + noeud["metadata"]["name"]], capture_output=True, text=True, check=True).stdout)
demande = sum(milli(((c.get("resources") or {}).get("requests") or {}).get("cpu", "0"))
              for p in pods["items"] if p["status"].get("phase") not in ("Succeeded", "Failed")
              for c in p["spec"]["containers"])
print((alloue - demande) // 4)
')
test "$PART" -ge 50
echo "allocatable de $NOEUD réparti : quatre parts de ${PART}m"

cat <<YAML | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: remplissage
  namespace: ${NS}
spec:
  replicas: 4
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: remplissage
  template:
    metadata:
      labels:
        app: remplissage
    spec:
      nodeSelector:
        kubernetes.io/hostname: ${NOEUD}
      terminationGracePeriodSeconds: 5
      containers:
        - name: lot
          image: ${BUSYBOX}
          command: ["sh", "-c", "sleep infinity"]
          resources:
            requests:
              cpu: ${PART}m
YAML
kubectl -n "$NS" rollout status deployment/remplissage --timeout=180s

install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/lab"
cat > "${LAB_HOME}/lab/urgent.yaml" <<YAML
apiVersion: v1
kind: Pod
metadata:
  name: urgent
  namespace: ${NS}
spec:
  nodeSelector:
    kubernetes.io/hostname: ${NOEUD}
  containers:
    - name: urgent
      image: ${BUSYBOX}
      command: ["sh", "-c", "sleep infinity"]
      resources:
        requests:
          cpu: ${PART}m
YAML
chown "$LAB_USER:$LAB_USER" "${LAB_HOME}/lab/urgent.yaml"
echo "Lab posé : ${NOEUD} est plein, ~/lab/urgent.yaml demande une part de plus."
