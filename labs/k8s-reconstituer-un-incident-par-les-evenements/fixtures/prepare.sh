#!/usr/bin/env bash
# Pose l'incident : cinq applications dans le namespace boutique. Quatre
# portent chacune une panne dont les Events Warning ont une raison différente
# (FailedScheduling, FailedMount, Unhealthy, BackOff), une est saine. Le
# tirage est neuf à chaque passage : quelle application porte quelle panne, et
# l'ordre de création, espacé de 30 secondes pour que la chronologie des Events
# soit nette.
#
# Rejouable : le namespace est recréé.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

NS=boutique
IMAGE='busybox:1.37@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e'

if [[ "$(kubectl get namespace "$NS" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete "namespace/$NS" --timeout=180s
fi
kubectl delete namespace "$NS" --ignore-not-found --wait=true
kubectl create namespace "$NS"

# L'image est tirée d'avance sur chaque nœud : sans cela, le premier Pod créé
# paierait le tirage et la chronologie des Events dépendrait du réseau.
for noeud in $(kubectl get nodes -o name | cut -d/ -f2); do
  kubectl -n "$NS" run "tirage-${noeud%%.*}" --image="$IMAGE" --restart=Never \
    --overrides="{\"spec\":{\"nodeName\":\"$noeud\",\"tolerations\":[{\"operator\":\"Exists\"}]}}" \
    --command -- true
done
kubectl -n "$NS" wait --for=jsonpath='{.status.phase}'=Succeeded pod --all --timeout=180s
kubectl -n "$NS" delete pod --all --wait=true

mapfile -t apps < <(printf '%s\n' panier paiement catalogue stock avis | shuf)
mapfile -t pannes < <(printf '%s\n' ressources volume sonde plantage saine | shuf)

for i in "${!apps[@]}"; do
  app=${apps[$i]}
  commande='["sh", "-c", "sleep 36000"]'
  extra_conteneur=''
  extra_spec=''
  requetes='{cpu: 10m, memory: 16Mi}'
  case "${pannes[$i]}" in
    ressources) requetes='{cpu: "64", memory: 16Mi}' ;;
    volume)
      extra_conteneur='        volumeMounts: [{name: config, mountPath: /etc/app}]'
      extra_spec='      volumes: [{name: config, configMap: {name: config-absente}}]'
      ;;
    sonde)
      extra_conteneur='        readinessProbe: {exec: {command: ["sh", "-c", "test -f /tmp/pret"]}, periodSeconds: 5}'
      ;;
    plantage) commande='["sh", "-c", "echo connexion refusée par la base; exit 1"]' ;;
    saine) ;;
  esac
  cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata: {name: $app, namespace: $NS}
spec:
  replicas: 1
  selector: {matchLabels: {app: $app}}
  template:
    metadata: {labels: {app: $app}}
    spec:
      containers:
      - name: app
        image: $IMAGE
        command: $commande
        resources:
          requests: $requetes
$extra_conteneur
$extra_spec
EOF
  # Le dernier n'a pas besoin d'attendre.
  if (( i < ${#apps[@]} - 1 )); then sleep 30; fi
done

sleep 20
kubectl -n "$NS" get pods -o wide
kubectl events -n "$NS" --types=Warning

echo "Incident posé : cinq applications dans boutique, dont quatre en panne."
