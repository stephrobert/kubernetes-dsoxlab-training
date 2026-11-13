#!/usr/bin/env bash
# Pose la situation : le Deployment inventaire, dont le Pod doit tourner
# sous un ServiceAccount qui n'existe pas. Le ReplicaSet le dit dans un
# event FailedCreate, et c'est cet event que le script attend : sans lui,
# la situation n'est pas posée.
#
# Rejouable : le namespace est attendu s'il se termine, et ce qu'un passage
# précédent aurait créé, ServiceAccount, Role, RoleBinding, est retiré pour
# que le Pod ne démarre pas tout seul.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace app-team -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/app-team --timeout=180s
fi
kubectl get namespace app-team >/dev/null 2>&1 || kubectl create namespace app-team

kubectl -n app-team delete rolebinding pod-reader-binding --ignore-not-found
kubectl -n app-team delete role pod-reader-role --ignore-not-found
kubectl -n app-team delete deployment inventaire affichage --ignore-not-found --wait=true
kubectl -n app-team delete serviceaccount pod-reader --ignore-not-found
# Un passage précédent a pu couper le jeton sur le ServiceAccount default :
# on le rend à son état d'origine, où le jeton est monté.
kubectl -n app-team patch serviceaccount default --type json \
  -p '[{"op":"remove","path":"/automountServiceAccountToken"}]' 2>/dev/null || true

# affichage sert une page et n'appelle jamais l'API. Il tourne sous le
# ServiceAccount default, qui monte un jeton dans chaque Pod : c'est ce jeton,
# inutile ici, que l'apprenant doit couper (D61).
cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: affichage
  namespace: app-team
spec:
  replicas: 1
  selector:
    matchLabels:
      app: affichage
  template:
    metadata:
      labels:
        app: affichage
    spec:
      containers:
        - name: affichage
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "mkdir -p /www && echo inventaire > /www/index.html && httpd -f -p 8080 -h /www"]
EOF
kubectl -n app-team rollout status deployment/affichage --timeout=180s

cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inventaire
  namespace: app-team
spec:
  replicas: 1
  selector:
    matchLabels:
      app: inventaire
  template:
    metadata:
      labels:
        app: inventaire
    spec:
      serviceAccountName: pod-reader
      containers:
        - name: inventaire
          image: curlimages/curl:8.22.0@sha256:58adaa4e8dca9c988bae2aba4ab3434a0bb2da16bbe3f92dec39ec7785166777
          command: ["sh", "-c", "sleep infinity"]
EOF

# La situation est posée quand le ReplicaSet a échoué à créer son Pod.
for essai in $(seq 1 30); do
  if kubectl -n app-team get events --field-selector reason=FailedCreate -o jsonpath='{.items[*].message}' | grep -q 'serviceaccount "pod-reader" not found'; then
    break
  fi
  sleep 2
done
kubectl -n app-team get events --field-selector reason=FailedCreate -o jsonpath='{.items[*].message}' | grep -q 'serviceaccount "pod-reader" not found'
kubectl -n app-team get deployment inventaire
echo "inventaire attend son ServiceAccount : aucun Pod ne peut être créé."
