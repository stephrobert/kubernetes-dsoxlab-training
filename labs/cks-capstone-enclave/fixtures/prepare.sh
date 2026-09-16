#!/usr/bin/env bash
# Pose la situation du capstone : deux espaces, deux temoins, et RIEN de ce
# que le candidat doit produire.
#
# Le Pod `autorise` est pose DANS l'enclave, avant que le candidat n'y impose
# quoi que ce soit. C'est deliberé : l'admission ne juge qu'a la CREATION, un
# Pod deja la survit a la regle qu'on pose ensuite. Il est neanmoins ecrit
# conforme au niveau `restricted`, pour qu'un candidat qui le supprimerait
# puisse le recreer a l'identique.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

# Tout ce que le candidat doit produire est retire s'il traine d'un passage
# precedent : sans cela, le capstone rendrait des points avant le travail.
kubectl delete namespace enclave dehors --ignore-not-found --wait=true --timeout=180s
kubectl get clusterrole,clusterrolebinding -o name 2>/dev/null \
  | grep -E 'enclave|coffre' | xargs -r kubectl delete --ignore-not-found || true

kubectl create namespace enclave
kubectl create namespace dehors

kubectl apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: autorise
  namespace: enclave
  labels:
    role: appelant
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: outil
      image: busybox:1.37
      command: ["sh", "-c", "sleep 86400"]
      securityContext:
        allowPrivilegeEscalation: false
        capabilities:
          drop: [ALL]
---
apiVersion: v1
kind: Pod
metadata:
  name: intrus
  namespace: dehors
spec:
  containers:
    - name: outil
      image: busybox:1.37
      command: ["sh", "-c", "sleep 86400"]
YAML

kubectl -n enclave wait --for=condition=ready pod/autorise --timeout=240s
kubectl -n dehors wait --for=condition=ready pod/intrus --timeout=240s

kubectl get namespace enclave --show-labels
echo "Situation posee : deux espaces, deux temoins, et rien d'autre."
