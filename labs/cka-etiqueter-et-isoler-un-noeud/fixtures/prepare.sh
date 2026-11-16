#!/usr/bin/env bash
# Pose la situation : l'équipe data veut se réserver k8s-w2.lab.
#   rapports  appartient à une autre équipe : deux réplicas, un sur k8s-w1.lab,
#             un sur k8s-w2.lab, qui devra partir ;
#   entrepot  appartient à l'équipe data : il exige equipe=data et tolère la
#             réserve, et reste en Pending tant que le nœud n'est pas étiqueté.
#
# Rejouable : k8s-w2.lab est remis nu (ni étiquette d'équipe, ni rôle, ni
# taint, ni annotation de contact) avant de reposer les deux applications.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

NS=equipes
NOEUD=k8s-w2.lab
IMAGE='nginx:1.27@sha256:6784fb0834aa7dbbe12e3d7471e69c290df3e6ba810dc38b34ae33d3c1c05f7d'

kubectl taint nodes "$NOEUD" equipe- || true
kubectl label nodes --all equipe- node-role.kubernetes.io/data- || true
kubectl annotate node "$NOEUD" maintenance-contact- || true

if [[ "$(kubectl get namespace "$NS" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete "namespace/$NS" --timeout=180s
fi
kubectl delete namespace "$NS" --ignore-not-found --wait=true
kubectl create namespace "$NS"

cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata: {name: rapports, namespace: $NS}
spec:
  replicas: 2
  selector: {matchLabels: {app: rapports}}
  template:
    metadata: {labels: {app: rapports}}
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - {key: kubernetes.io/hostname, operator: In, values: [k8s-w1.lab, k8s-w2.lab]}
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector: {matchLabels: {app: rapports}}
              topologyKey: kubernetes.io/hostname
      containers:
      - name: app
        image: $IMAGE
---
apiVersion: apps/v1
kind: Deployment
metadata: {name: entrepot, namespace: $NS}
spec:
  replicas: 1
  selector: {matchLabels: {app: entrepot}}
  template:
    metadata: {labels: {app: entrepot}}
    spec:
      nodeSelector: {equipe: data}
      tolerations:
      - {key: equipe, operator: Equal, value: data}
      containers:
      - name: app
        image: $IMAGE
EOF

# Un Pod de rapports doit être sur k8s-w2.lab au départ, sinon le test
# d'éviction ne mesurerait rien. L'anti-affinité n'est que préférée : si les
# deux réplicas se retrouvent ensemble, on en recrée un jusqu'à les séparer.
kubectl -n "$NS" rollout status deployment/rapports --timeout=180s
for essai in $(seq 1 10); do
  noeuds=$(kubectl -n "$NS" get pods -l app=rapports -o jsonpath='{range .items[*]}{.spec.nodeName}{"\n"}{end}' | sort -u)
  grep -qx "$NOEUD" <<<"$noeuds" && [[ $(wc -l <<<"$noeuds") -eq 2 ]] && break
  kubectl -n "$NS" delete "$(kubectl -n "$NS" get pods -l app=rapports -o name | head -1)" --wait=true
  kubectl -n "$NS" rollout status deployment/rapports --timeout=180s
done
kubectl -n "$NS" get pods -o wide

echo "Situation posée : rapports a un Pod sur $NOEUD, entrepot attend un nœud de l'équipe data."
