#!/usr/bin/env bash
# Pose la situation du lab k8s-faire-sortir-le-trafic-par-une-passerelle, sur
# le cluster net-* que le setup vient de ramener aux valeurs du socle (Cilium
# 1.20.5, passerelle d'egress désactivée, masquage par iptables) :
#
# - le namespace egress-demo et deux Pods sur net-w1.lab : sortie-controlee,
#   que la politique doit viser, et autre, qu'elle ne doit pas toucher ;
# - la ConfigMap temoin, qui donne l'URL du serveur témoin lancé par le setup
#   sur k8s-cp.lab, hors du cluster.
#
# Rien de ce que l'apprenant doit produire n'existe : ni passerelle activée, ni
# nœud étiqueté, ni CiliumEgressGatewayPolicy. Rejouable.
#
# TEMOIN_URL est passée par le setup.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

BUSYBOX="busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e"

kubectl delete ciliumegressgatewaypolicies.cilium.io --all --ignore-not-found --wait=true 2>/dev/null || true
for n in $(kubectl get nodes -o name); do kubectl label "$n" egress-gateway- 2>/dev/null || true; done
kubectl delete namespace egress-demo --ignore-not-found --wait=true --timeout=180s

kubectl create namespace egress-demo
kubectl -n egress-demo create configmap temoin --from-literal=url="$TEMOIN_URL"
kubectl apply -f - <<YAML
apiVersion: v1
kind: Pod
metadata:
  name: sortie-controlee
  namespace: egress-demo
  labels: {app: sortie-controlee}
spec:
  nodeName: net-w1.lab
  containers:
    - {name: c, image: "$BUSYBOX", command: [sleep, "36000"]}
---
apiVersion: v1
kind: Pod
metadata:
  name: autre
  namespace: egress-demo
  labels: {app: autre}
spec:
  nodeName: net-w1.lab
  containers:
    - {name: c, image: "$BUSYBOX", command: [sleep, "36000"]}
YAML
kubectl -n egress-demo wait --for=condition=Ready pod --all --timeout=180s

# Départ : les deux Pods sortent par leur propre nœud, net-w1.lab.
for p in sortie-controlee autre; do
  kubectl -n egress-demo exec "$p" -- wget -qO- -T 5 "$TEMOIN_URL"
done
echo "Situation posée : passerelle désactivée, deux Pods sur net-w1, témoin à $TEMOIN_URL."
