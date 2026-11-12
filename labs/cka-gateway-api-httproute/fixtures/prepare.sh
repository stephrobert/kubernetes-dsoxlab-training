#!/usr/bin/env bash
# Pose la situation : deux applications distinctes, deja exposees, et AUCUNE
# regle de routage.
#
# Les deux applications repondent leur NOM, et c'est tout l'interet : le lab
# herite servait nginx des deux cotes, si bien qu'aucun test ne pouvait
# distinguer un routage correct d'un routage inverse, ni meme d'un routage
# inexistant.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

# Ce que le candidat doit produire est retire s'il traine d'un passage
# precedent : sans cela, le lab rendrait 100 avant le travail.
kubectl -n lab delete gateway --all --ignore-not-found 2>/dev/null || true

if [[ "$(kubectl get namespace lab -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/lab --timeout=180s
fi
kubectl get namespace lab >/dev/null 2>&1 || kubectl create namespace lab
# Seule la route que le candidat ecrit est retiree ; catalogue est reposee plus bas.
kubectl -n lab delete httproute --all --ignore-not-found 2>/dev/null || true

kubectl apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-app
  namespace: lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
        - name: echo
          image: hashicorp/http-echo:1.0.0@sha256:fcb75f691c8b0414d670ae570240cbf95502cc18a9ba57e982ecac589760a186
          args: ["-text=api", "-listen=:5678"]
          ports:
            - containerPort: 5678
---
apiVersion: v1
kind: Service
metadata:
  name: svc-api
  namespace: lab
spec:
  selector:
    app: api
  ports:
    - port: 80
      targetPort: 5678
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: echo
          image: hashicorp/http-echo:1.0.0@sha256:fcb75f691c8b0414d670ae570240cbf95502cc18a9ba57e982ecac589760a186
          args: ["-text=web", "-listen=:5678"]
          ports:
            - containerPort: 5678
---
apiVersion: v1
kind: Service
metadata:
  name: svc-web
  namespace: lab
spec:
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 5678
YAML

# La panne a reparer : l'equipe boutique sert son catalogue dans SON namespace,
# et une HTTPRoute de lab l'y envoie sans que boutique l'ait autorise. Le
# controleur refuse la reference (ResolvedRefs=False, RefNotPermitted) : la
# route existe, est acceptee, et ne sert rien. Toute autorisation d'un passage
# precedent est retiree.
if [[ "$(kubectl get namespace boutique -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/boutique --timeout=180s
fi
kubectl get namespace boutique >/dev/null 2>&1 || kubectl create namespace boutique
kubectl -n boutique delete referencegrant --all --ignore-not-found
kubectl -n lab delete referencegrant --all --ignore-not-found

kubectl apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: catalogue
  namespace: boutique
spec:
  replicas: 1
  selector:
    matchLabels:
      app: catalogue
  template:
    metadata:
      labels:
        app: catalogue
    spec:
      containers:
        - name: echo
          image: hashicorp/http-echo:1.0.0@sha256:fcb75f691c8b0414d670ae570240cbf95502cc18a9ba57e982ecac589760a186
          args: ["-text=catalogue", "-listen=:5678"]
          ports:
            - containerPort: 5678
---
apiVersion: v1
kind: Service
metadata:
  name: svc-catalogue
  namespace: boutique
spec:
  selector:
    app: catalogue
  ports:
    - port: 80
      targetPort: 5678
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: catalogue
  namespace: lab
spec:
  parentRefs:
    - name: entree
  hostnames:
    - catalogue.local
  rules:
    - backendRefs:
        - name: svc-catalogue
          namespace: boutique
          port: 80
YAML
kubectl -n boutique rollout status deployment/catalogue --timeout=240s

kubectl -n lab rollout status deployment/api-app --timeout=240s
kubectl -n lab rollout status deployment/web-app --timeout=240s

# On montre l'etat de depart dans le journal.
curl -s --resolve app.local:30080:127.0.0.1 http://app.local:30080/api \
  --max-time 8 -w ' [%{http_code}]\n' || true
echo "Situation posee : les deux applications servent, et rien ne les route."
