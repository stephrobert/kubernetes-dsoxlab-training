#!/usr/bin/env bash
# Pose la situation du challenge, dans le namespace livraison :
#
#   - un registre local, en hostNetwork sur le port 5000 du plan de contrôle,
#     qui porte deux images non signées (repris de cks-cosign-verify-image) ;
#   - le Deployment vitrine, sur un TAG (repris de cks-image-pinned-digest) ;
#   - le Deployment boutique, sur une image de 2021 (repris de
#     cks-image-scanning-trivy) ;
#   - Kyverno, le moteur d'admission, sans aucune politique.
#
# KYVERNO ET LE REGISTRE. Les images s'appellent localhost:5000/... : sur le
# nœud, c'est le registre. Dans le Pod de Kyverno, localhost est le Pod
# lui-même. Un petit relais socat, ajouté au Pod du contrôleur d'admission,
# écoute sur son port 5000 et renvoie vers le Service du registre : Kyverno lit
# donc les images et leurs signatures à la même adresse que cosign sur le
# nœud, et la politique de l'apprenant nomme une seule adresse.
#
# Kyverno est réduit à son contrôleur d'admission : les trois autres
# contrôleurs (rapports, tâches de fond, nettoyage) ne servent pas à vérifier
# une signature, et pèsent sur un plan de contrôle de 4 Go.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne rend que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

: "${KYVERNO_VERSION:?la version de Kyverno manque}"
: "${KYVERNO_MANIFESTE:?le chemin du manifeste Kyverno manque}"
NS=livraison

if [[ "$(kubectl get namespace "$NS" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete "namespace/$NS" --timeout=180s
fi
kubectl get namespace livraison >/dev/null 2>&1 || kubectl create namespace livraison

# --- Kyverno : installé une fois, puis remis sans politique à chaque passage.
deja=$(kubectl -n kyverno get deployment kyverno-admission-controller \
  -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null || true)
if [[ "$deja" != *":v${KYVERNO_VERSION}" ]]; then
  # Côté serveur : les CRD de Kyverno dépassent la taille d'annotation d'un
  # apply côté client.
  kubectl apply --server-side --force-conflicts -f "$KYVERNO_MANIFESTE"
fi

conteneurs=$(kubectl -n kyverno get deployment kyverno-admission-controller \
  -o jsonpath='{.spec.template.spec.containers[*].name}')
if [[ " $conteneurs " != *" relais-registre "* ]]; then
  kubectl -n kyverno patch deployment kyverno-admission-controller --type=json -p '[
    {"op": "add", "path": "/spec/template/spec/containers/-", "value": {
      "name": "relais-registre",
      "image": "alpine/socat:1.8.1.1",
      "args": ["TCP-LISTEN:5000,fork,reuseaddr", "TCP:registre.livraison.svc.cluster.local:5000"],
      "resources": {"requests": {"cpu": "10m", "memory": "16Mi"}, "limits": {"memory": "64Mi"}},
      "securityContext": {
        "runAsNonRoot": true, "runAsUser": 65534, "allowPrivilegeEscalation": false,
        "readOnlyRootFilesystem": true, "capabilities": {"drop": ["ALL"]}
      }
    }}
  ]'
fi
arguments=$(kubectl -n kyverno get deployment kyverno-admission-controller \
  -o jsonpath='{.spec.template.spec.containers[0].args}')
if [[ "$arguments" != *"--allowInsecureRegistry=true"* ]]; then
  # Un drapeau répété : le dernier l'emporte. Le registre local parle HTTP, et
  # les rapports d'admission resteraient sans le contrôleur qui les range.
  kubectl -n kyverno patch deployment kyverno-admission-controller --type=json -p '[
    {"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--allowInsecureRegistry=true"},
    {"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--admissionReports=false"}
  ]'
fi
kubectl -n kyverno scale deployment kyverno-background-controller \
  kyverno-cleanup-controller kyverno-reports-controller --replicas=0
kubectl -n kyverno rollout status deployment/kyverno-admission-controller --timeout=300s

# Le contrôleur pose ses webhooks lui-même, une fois prêt : sans celui qui
# valide les politiques, l'apprenant ne pourrait encore rien poser.
for _ in $(seq 1 60); do
  kubectl get validatingwebhookconfiguration kyverno-policy-validating-webhook-cfg >/dev/null 2>&1 && break
  sleep 3
done
kubectl get validatingwebhookconfiguration kyverno-policy-validating-webhook-cfg

# Les politiques d'un passage précédent : sans cela, l'état 10 serait vrai
# avant tout travail.
kubectl delete clusterpolicies.kyverno.io --all --ignore-not-found --wait=true
kubectl delete policies.kyverno.io --all --all-namespaces --ignore-not-found --wait=true

# --- La signature : clés et ConfigMap d'un passage précédent retirés.
rm -f /root/cosign.key /root/cosign.pub
kubectl -n livraison delete configmap cosign-pub-key --ignore-not-found --wait=true

# --- Le registre local, recréé vide à chaque passage.
kubectl -n livraison delete pod registre --ignore-not-found --wait=true
kubectl apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: registre
  namespace: livraison
  labels:
    app: registre
spec:
  nodeName: k8s-cp.lab
  hostNetwork: true
  containers:
    - name: registry
      image: registry:2
      ports:
        - containerPort: 5000
          hostPort: 5000
---
apiVersion: v1
kind: Service
metadata:
  name: registre
  namespace: livraison
spec:
  selector:
    app: registre
  ports:
    - port: 5000
      targetPort: 5000
YAML
kubectl -n livraison wait --for=condition=ready pod/registre --timeout=180s
for _ in $(seq 1 30); do
  curl -sf http://localhost:5000/v2/ >/dev/null 2>&1 && break
  sleep 2
done
curl -sf http://localhost:5000/v2/ >/dev/null

crane copy nginx:1.27-alpine localhost:5000/appli/web:1.0
crane copy busybox:1.37 localhost:5000/appli/outil:1.0
crane ls localhost:5000/appli/web
crane ls localhost:5000/appli/outil

# --- Les deux Deployments, reposés à chaque passage, image comprise.
kubectl -n livraison delete deployment vitrine boutique --ignore-not-found --wait=true
kubectl apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vitrine
  namespace: livraison
  labels:
    app: vitrine
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
        - name: web
          image: nginx:1.27-alpine
          ports:
            - containerPort: 80
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: boutique
  namespace: livraison
  labels:
    app: boutique
spec:
  replicas: 2
  selector:
    matchLabels:
      app: boutique
  template:
    metadata:
      labels:
        app: boutique
    spec:
      containers:
        - name: web
          image: nginx:1.21
          ports:
            - containerPort: 80
YAML
kubectl -n livraison rollout status deployment/vitrine --timeout=300s
kubectl -n livraison rollout status deployment/boutique --timeout=300s

# Le test de l'état 2 interroge le runtime du PLAN DE CONTRÔLE : l'image doit
# y être connue même si les deux réplicas tournent sur le worker.
crictl pull nginx:1.27-alpine

# La base de vulnérabilités, téléchargée MAINTENANT : sans elle, le premier
# scan passerait plusieurs minutes à la tirer.
trivy image --quiet --download-db-only 2>&1 | tail -3 || true

# Point de départ vérifié : sans politique, l'image non signée est admise.
kubectl -n livraison run sonde-depart --image=localhost:5000/appli/outil:1.0 \
  --restart=Never --dry-run=server -o name

echo "Situation posée : registre sans signature, vitrine sur un tag, boutique sur nginx:1.21, Kyverno sans politique."
