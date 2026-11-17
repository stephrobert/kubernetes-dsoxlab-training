#!/usr/bin/env bash
# Pose la situation du lab k8s-annoncer-un-service-en-bgp, sur le cluster net-*
# que le setup vient de ramener aux valeurs du socle (Cilium 1.20.5, plan de
# contrôle BGP désactivé) :
#
# - le namespace bgp-demo, une application web (nginx) et son Service de type
#   LoadBalancer, étiqueté annonce-bgp=oui. Sans pool d'adresses, il reste en
#   <pending> : ce cluster n'a pas de répartiteur de charge.
#
# Le routeur FRR, lui, est lancé par le setup sur l'hôte témoin. Rien de ce
# que l'apprenant doit produire n'existe : ni BGP activé, ni pool, ni
# configuration BGP, ni nœud étiqueté. Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

NGINX="nginx:1.27@sha256:6784fb0834aa7dbbe12e3d7471e69c290df3e6ba810dc38b34ae33d3c1c05f7d"

# Ce qu'un passage précédent a laissé. Les ressources BGP n'existent que si
# leur CRD existe : on ignore l'absence de type.
for type in ciliumbgpclusterconfigs ciliumbgppeerconfigs ciliumbgpadvertisements ciliumloadbalancerippools; do
  kubectl delete "$type.cilium.io" --all --ignore-not-found --wait=true 2>/dev/null || true
done
for n in $(kubectl get nodes -o name); do kubectl label "$n" bgp- 2>/dev/null || true; done
kubectl delete namespace bgp-demo --ignore-not-found --wait=true --timeout=180s

kubectl create namespace bgp-demo
kubectl apply -f - <<YAML
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: bgp-demo
spec:
  replicas: 2
  selector:
    matchLabels: {app: web}
  template:
    metadata:
      labels: {app: web}
    spec:
      containers:
        - name: nginx
          image: "$NGINX"
          ports:
            - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: bgp-demo
  labels:
    annonce-bgp: oui
spec:
  type: LoadBalancer
  selector: {app: web}
  ports:
    - {name: http, port: 80}
YAML
kubectl -n bgp-demo rollout status deployment/web --timeout=180s
kubectl -n bgp-demo get service web
echo "Situation posée : Service web en LoadBalancer, sans adresse, BGP désactivé."
