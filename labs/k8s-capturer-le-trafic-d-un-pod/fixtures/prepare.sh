#!/usr/bin/env bash
# Pose la situation du lab k8s-capturer-le-trafic-d-un-pod : dans le namespace
# boutique, trois clients appellent chacun leur service, et chaque appel échoue
# d'une façon différente. Les trois pannes sont tirées au hasard à chaque
# passage, pour qu'aucune réponse ne se recopie d'un passage à l'autre :
#
#   refus : le Service vise un port où rien n'écoute (targetPort 5679) ;
#   perte : une NetworkPolicy d'entrée sur le serveur n'admet personne d'utile ;
#   dns   : le client appelle un nom de Service mal écrit (un « s » de trop).
#
# Les clients ne journalisent qu'un échec générique, sans la cause : c'est la
# capture qui la dit. Une affinité les écarte du control plane (qui accepte
# des Pods dans ce cluster, mesuré le 2026-11-15) et une contrainte de
# répartition les place sur les deux workers. Rejouable : le namespace est
# recréé à chaque passage.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

kubectl delete namespace boutique --ignore-not-found --wait=true --timeout=240s
kubectl create namespace boutique

# Couples client -> serveur, et pannes tirées au hasard.
clients=(commandes factures livraisons)
serveurs=(catalogue paiement transport)
mapfile -t pannes < <(printf '%s\n' refus perte dns | shuf)

for i in 0 1 2; do
  client=${clients[$i]}
  serveur=${serveurs[$i]}
  panne=${pannes[$i]}
  port_cible=5678
  cible=$serveur
  [ "$panne" = refus ] && port_cible=5679
  [ "$panne" = dns ] && cible="${serveur}s"

  kubectl -n boutique apply -f - <<YAML
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $serveur
  labels: {app: $serveur, tier: serveur}
spec:
  replicas: 1
  selector: {matchLabels: {app: $serveur}}
  template:
    metadata: {labels: {app: $serveur, tier: serveur}}
    spec:
      containers:
        - name: http
          image: hashicorp/http-echo:1.0.0
          args: ["-listen=:5678", "-text=$serveur"]
          ports: [{containerPort: 5678}]
---
apiVersion: v1
kind: Service
metadata: {name: $serveur}
spec:
  selector: {app: $serveur}
  ports: [{port: 80, targetPort: $port_cible}]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $client
  labels: {app: $client, tier: client}
spec:
  replicas: 1
  selector: {matchLabels: {app: $client}}
  template:
    metadata: {labels: {app: $client, tier: client}}
    spec:
      # Le control plane de ce cluster accepte des Pods : sans cette
      # affinité, un client s'y place et la capture se fait sans ssh.
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - {key: node-role.kubernetes.io/control-plane, operator: DoesNotExist}
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: DoNotSchedule
          labelSelector: {matchLabels: {tier: client}}
      containers:
        - name: app
          image: curlimages/curl:8.22.0
          env:
            - {name: CIBLE, value: "http://$cible/"}
          command:
            - sh
            - -c
            - |
              while true; do
                if curl -s -m 8 -o /dev/null "\$CIBLE"; then
                  echo "\$(date +%T) appel vers \$CIBLE réussi"
                else
                  echo "\$(date +%T) appel vers \$CIBLE en échec"
                fi
                sleep 2
              done
YAML

  if [ "$panne" = perte ]; then
    kubectl -n boutique apply -f - <<YAML
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: ${serveur}-entree}
spec:
  podSelector: {matchLabels: {app: $serveur}}
  policyTypes: [Ingress]
  ingress:
    - from: [{podSelector: {matchLabels: {role: inventaire}}}]
YAML
  fi
done

kubectl -n boutique wait --for=condition=Available deployment --all --timeout=300s
kubectl -n boutique get pods -o wide
