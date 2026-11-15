#!/usr/bin/env bash
# Pose la situation : une CA interne servie par le ClusterIssuer ca-formation,
# l'application vitrine qui repond en HTTP dans son namespace, et RIEN de ce que
# l'apprenant doit produire (ni certificat dans vitrine, ni Gateway, ni route).
#
# La CA est construite comme dans k8s-emettre-un-certificat-avec-cert-manager :
# un ClusterIssuer auto-signe d'amorce signe un certificat d'autorite, range
# dans le namespace cert-manager (le « cluster resource namespace » ou un
# ClusterIssuer lit ses Secrets), puis un ClusterIssuer de type CA s'en sert.
# Rejouable : le namespace de travail est recree a chaque passage.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

# Ce que l'apprenant doit produire disparait avec le namespace : sans cela, un
# second `run` rendrait les tests vrais avant le travail.
kubectl delete namespace vitrine --ignore-not-found --wait=true --timeout=240s

# Le webhook de cert-manager peut refuser quelques secondes apres son
# demarrage : on reessaie.
for essai in $(seq 1 30); do
  if kubectl apply -f - <<'YAML'
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: amorce-auto-signee
spec:
  selfSigned: {}
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: ca-formation
  namespace: cert-manager
spec:
  isCA: true
  commonName: CA de la formation
  subject:
    organizations:
      - Formation Kubernetes
  secretName: ca-formation
  duration: 8760h
  privateKey:
    algorithm: ECDSA
    size: 256
  issuerRef:
    name: amorce-auto-signee
    kind: ClusterIssuer
    group: cert-manager.io
---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: ca-formation
spec:
  ca:
    secretName: ca-formation
YAML
  then break; fi
  echo "webhook de cert-manager pas encore pret (essai ${essai})"
  sleep 5
done

kubectl -n cert-manager wait --for=condition=Ready certificate/ca-formation --timeout=180s
kubectl wait --for=condition=Ready clusterissuer/ca-formation --timeout=180s

kubectl create namespace vitrine

kubectl apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vitrine
  namespace: vitrine
spec:
  replicas: 2
  selector:
    matchLabels:
      app: vitrine
  template:
    metadata:
      labels:
        app: vitrine
    spec:
      containers:
        - name: echo
          image: hashicorp/http-echo:1.0.0@sha256:fcb75f691c8b0414d670ae570240cbf95502cc18a9ba57e982ecac589760a186
          args: ["-text=vitrine", "-listen=:5678"]
          ports:
            - containerPort: 5678
---
apiVersion: v1
kind: Service
metadata:
  name: vitrine
  namespace: vitrine
spec:
  selector:
    app: vitrine
  ports:
    - name: http
      port: 80
      targetPort: 5678
YAML

kubectl -n vitrine rollout status deployment/vitrine --timeout=240s
kubectl get clusterissuer
kubectl -n vitrine get deploy,svc
echo "Situation posee : la CA ca-formation est prete, vitrine repond en HTTP, aucune Gateway."
