#!/usr/bin/env bash
# Pose la situation du lab k8s-explorer-l-api sur le cluster kind « lab » :
#
#   - une CRD inventée, Export, du groupe donnees.formation.k8s, servie en DEUX
#     versions : v1alpha1, ancienne et pauvre, et v1, celle que sert
#     `api-resources`, dont le schéma exige trois champs et ferme la liste des
#     formats. Seuls `api-resources` puis `kubectl explain` le révèlent ;
#   - le namespace entrepot, avec ce que `kubectl get all` ne montre pas
#     (ConfigMap, Secret, ServiceAccount, ResourceQuota, NetworkPolicy,
#     PodDisruptionBudget) et un Deployment annuaire SANS sonde de
#     disponibilité, qui écoute sur 8080, port nommé web ;
#   - ~/entrepot/, vide, où l'apprenant écrit son relevé.
#
# La CRD est attendue jusqu'à ce que `kubectl explain` connaisse son schéma :
# mesuré le 2026-11-11, il arrive environ 1 s APRÈS la condition Established.
# Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
AGNHOST="registry.k8s.io/e2e-test-images/agnhost:2.61@sha256:101f3357d1ad890c3090e78ea6c6a47dc5137cbe19836796e13d5dcb2b84d2e6"
CRD="exports.donnees.formation.k8s"

# L'ancienne situation (avant le 2026-11-20) est retirée aussi : un cluster qui
# l'a connue ne doit pas garder sa CRD.
kubectl delete namespace entrepot archives --ignore-not-found --wait=true --timeout=180s
kubectl delete crd "$CRD" sauvegardes.sauvegarde.formation.k8s --ignore-not-found --wait=true --timeout=120s

kubectl apply -f - <<'EOF'
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: exports.donnees.formation.k8s
spec:
  group: donnees.formation.k8s
  scope: Namespaced
  names:
    plural: exports
    singular: export
    kind: Export
    shortNames:
      - exp
  versions:
    - name: v1alpha1
      served: true
      storage: false
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                base:
                  type: string
                  description: Nom de la base à exporter.
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required:
                - base
                - planification
                - format
              properties:
                base:
                  type: string
                  description: Nom de la base de données à exporter.
                planification:
                  type: string
                  description: Quand exporter, en expression cron à cinq champs (minute heure jour mois jour-de-semaine, 1 pour lundi).
                format:
                  type: string
                  enum:
                    - csv
                    - json
                    - parquet
                  description: Format du fichier produit.
                lignes:
                  type: integer
                  minimum: 1
                  maximum: 100000
                  description: Nombre maximal de lignes par fichier. Facultatif.
EOF
kubectl wait --for=condition=Established "crd/$CRD" --timeout=60s
for _ in $(seq 1 30); do
  kubectl explain export.spec --api-version=donnees.formation.k8s/v1 >/dev/null 2>&1 && break
  sleep 1
done
kubectl explain export.spec --api-version=donnees.formation.k8s/v1 >/dev/null

kubectl create namespace entrepot
kubectl -n entrepot create configmap annuaire-config --from-literal=LANGUE=fr
kubectl -n entrepot create secret generic annuaire-db --from-literal=DB_PASSWORD=Entrepot-2026
kubectl -n entrepot create serviceaccount annuaire
kubectl -n entrepot create quota entrepot-quota --hard=pods=10,configmaps=20
kubectl -n entrepot create poddisruptionbudget annuaire-pdb --selector=app=annuaire --min-available=1
kubectl -n entrepot apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: autoriser-tout
spec:
  podSelector: {}
  ingress:
    - {}
  policyTypes:
    - Ingress
EOF
kubectl -n entrepot apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: annuaire
spec:
  replicas: 2
  selector:
    matchLabels:
      app: annuaire
  template:
    metadata:
      labels:
        app: annuaire
    spec:
      serviceAccountName: annuaire
      containers:
        - name: annuaire
          image: ${AGNHOST}
          command: ["/agnhost", "netexec", "--http-port=8080"]
          ports:
            - name: web
              containerPort: 8080
EOF
kubectl -n entrepot rollout status deployment annuaire --timeout=180s

rm -rf "${LAB_HOME:?}/archives" "${LAB_HOME:?}/entrepot"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/entrepot"
echo "Situation posée : CRD Export en deux versions, namespace entrepot, annuaire sans sonde."
