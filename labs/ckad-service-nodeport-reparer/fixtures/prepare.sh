#!/usr/bin/env bash
# Pose la situation : l'application accueil tourne et répond son nom, mais le
# Service NodePort qui devait la publier a été écrit de travers. Son sélecteur
# ne vise aucun Pod, son targetPort ne correspond pas au port du conteneur, et
# son NodePort est celui que Kubernetes a tiré au hasard.
#
# Rejouable : le namespace est attendu s'il se termine, et le Service est
# recréé à l'identique, ce qui remet la panne.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace guichet -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/guichet --timeout=180s
fi
kubectl get namespace guichet >/dev/null 2>&1 || kubectl create namespace guichet
kubectl -n guichet delete service accueil --ignore-not-found --wait=true

cat <<'YAML' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: accueil
  namespace: guichet
spec:
  replicas: 2
  selector:
    matchLabels:
      app: accueil
  template:
    metadata:
      labels:
        app: accueil
    spec:
      containers:
        - name: echo
          image: hashicorp/http-echo:1.0.0@sha256:fcb75f691c8b0414d670ae570240cbf95502cc18a9ba57e982ecac589760a186
          args: ["-text=accueil", "-listen=:5678"]
          ports:
            - containerPort: 5678
---
apiVersion: v1
kind: Service
metadata:
  name: accueil
  namespace: guichet
spec:
  type: NodePort
  selector:
    app: acceuil
  ports:
    - port: 80
      targetPort: 8080
YAML

kubectl -n guichet rollout status deployment/accueil --timeout=180s

# La situation : le Service existe, mais rien ne répond sur son NodePort.
NP="$(kubectl -n guichet get service accueil -o jsonpath='{.spec.ports[0].nodePort}')"
# Le tirage ne doit pas tomber sur le port demandé : le lab passerait avant le
# travail. Une chance sur 2768, et on retire alors.
while [[ "$NP" == 30091 ]]; do
  kubectl -n guichet get service accueil -o json \
    | python3 -c 'import json,sys; s=json.load(sys.stdin); del s["spec"]["ports"][0]["nodePort"]; [s["metadata"].pop(k,None) for k in ("resourceVersion","uid","creationTimestamp")]; s.pop("status",None); [s["spec"].pop(k,None) for k in ("clusterIP","clusterIPs")]; print(json.dumps(s))' > /tmp/dsoxlab-accueil.json
  kubectl -n guichet delete service accueil --wait=true
  kubectl apply -f /tmp/dsoxlab-accueil.json
  NP="$(kubectl -n guichet get service accueil -o jsonpath='{.spec.ports[0].nodePort}')"
done
rm -f /tmp/dsoxlab-accueil.json
test -z "$(kubectl -n guichet get endpointslices -l kubernetes.io/service-name=accueil \
  -o jsonpath='{.items[*].endpoints[*].addresses[*]}')"
if curl -s --max-time 3 "http://127.0.0.1:${NP}/"; then
  echo "le NodePort ${NP} répond : la situation n'est pas celle du scénario" >&2
  exit 1
fi
echo "Situation posée : accueil tourne, son Service NodePort ${NP} ne mène nulle part."
