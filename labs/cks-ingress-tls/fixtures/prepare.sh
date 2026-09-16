#!/usr/bin/env bash
# Pose la situation : un site derriere un Ingress qui n'a AUCUNE section TLS.
#
# Le piege du lab est la : le contrôleur repond deja en HTTPS sur son
# entrypoint securise, avec un certificat auto-signe generique qu'il fabrique
# au demarrage. Mesure le 2026-09-16 : `CN = TRAEFIK DEFAULT CERT`, et
# `curl -k` rend 200. Un test qui se contenterait de « le site repond en
# HTTPS » serait donc vert AVANT le travail.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

# Ce que le candidat doit produire est retire s'il traine d'un passage
# precedent : sans cela, le lab rendrait 100 avant le travail.
kubectl -n vitrine delete secret vitrine-tls --ignore-not-found 2>/dev/null || true

if [[ "$(kubectl get namespace vitrine -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/vitrine --timeout=180s
fi
kubectl get namespace vitrine >/dev/null 2>&1 || kubectl create namespace vitrine

kubectl apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: site
  namespace: vitrine
spec:
  replicas: 1
  selector:
    matchLabels:
      app: site
  template:
    metadata:
      labels:
        app: site
    spec:
      containers:
        - name: web
          image: nginxinc/nginx-unprivileged:1.27-alpine
          ports:
            - containerPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: site
  namespace: vitrine
spec:
  selector:
    app: site
  ports:
    - port: 80
      targetPort: 8080
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: site
  namespace: vitrine
spec:
  ingressClassName: traefik
  rules:
    - host: vitrine.lab
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: site
                port:
                  number: 80
YAML

kubectl -n vitrine rollout status deployment/site --timeout=240s

# On montre l'etat de depart dans le journal : il vaut mieux que le
# diagnostic d'un echec de setup porte la mesure plutot qu'une supposition.
echo | openssl s_client -connect 127.0.0.1:30443 -servername vitrine.lab 2>/dev/null \
  | openssl x509 -noout -subject || true
echo "Situation posee : le site repond, et le contrôleur sert son certificat par defaut."
