#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
# Elle tourne comme l'apprenant, avec son kubeconfig et son chart.
set -euo pipefail

helm version --short

# 1. Installer, révision 1, un replica.
helm install web ~/charts/web -n lab --set replicaCount=1 --wait --timeout 180s

# 2. Mettre à jour, révision 2, deux replicas.
helm upgrade web ~/charts/web -n lab --set replicaCount=2 --wait --timeout 180s

# 3. Revenir en arrière, révision 3, qui reprend la 1.
helm rollback web 1 -n lab --wait --timeout 180s

# La preuve : l'historique, et l'application qui répond.
helm history web -n lab
kubectl -n lab rollout status deployment/web --timeout=180s
IP=$(kubectl -n lab get service web -o jsonpath='{.spec.clusterIP}')
curl -sS -m 5 "http://${IP}/" | grep -i -m1 'nginx'
echo "web : install, upgrade, rollback, et l'application sert."
