#!/usr/bin/env bash
# Pose la situation du lab ckad-crd-ressource-personnalisee sur le cluster kind
# « lab » :
#
#   - la CRD sauvegardes.atelier.formation.k8s (kind Sauvegarde), la même que
#     la leçon « Operators et CRDs pour développeurs » ;
#   - le namespace sauvegardes, avec la ressource hebdomadaire (14 jours) et la
#     ressource ancienne, bloquée en Terminating par un finalizer que personne
#     ne retirera : aucun contrôleur ne surveille cette CRD ;
#   - ~/sauvegardes/, vide, où l'apprenant consigne ce qu'il lit de l'API.
#
# Les uid de la CRD et de hebdomadaire sont mémorisés dans
# /var/lib/dsoxlab/crd-ressource-personnalisee.json : hebdomadaire doit être
# modifiée sans être recréée, et la CRD doit rester celle du départ.
#
# Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
MEMOIRE=/var/lib/dsoxlab/crd-ressource-personnalisee.json

# Un passage précédent a pu laisser une ressource bloquée : on la libère avant
# de retirer le namespace, sinon sa suppression attendrait pour toujours.
if kubectl get crd sauvegardes.atelier.formation.k8s >/dev/null 2>&1; then
  for r in $(kubectl -n sauvegardes get sauvegardes -o name 2>/dev/null); do
    kubectl -n sauvegardes patch "$r" --type=merge -p '{"metadata":{"finalizers":null}}' || true
  done
fi
kubectl delete namespace sauvegardes --ignore-not-found --wait=true --timeout=180s
kubectl delete crd sauvegardes.atelier.formation.k8s --ignore-not-found --wait=true --timeout=120s

kubectl apply -f - <<'YAML'
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: sauvegardes.atelier.formation.k8s
spec:
  group: atelier.formation.k8s
  scope: Namespaced
  names:
    plural: sauvegardes
    singular: sauvegarde
    kind: Sauvegarde
    shortNames:
      - sauv
  versions:
    - name: v1
      served: true
      storage: true
      subresources:
        status: {}
      additionalPrinterColumns:
        - name: Source
          type: string
          jsonPath: .spec.source
        - name: Retention
          type: integer
          jsonPath: .spec.retentionJours
        - name: Phase
          type: string
          jsonPath: .status.phase
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required:
                - source
              properties:
                source:
                  type: string
                  description: Le volume à sauvegarder
                retentionJours:
                  type: integer
                  minimum: 1
                  maximum: 365
                  description: Durée de conservation en jours
            status:
              type: object
              properties:
                phase:
                  type: string
YAML
kubectl wait --for=condition=Established crd/sauvegardes.atelier.formation.k8s --timeout=60s

kubectl create namespace sauvegardes
kubectl apply -f - <<'YAML'
apiVersion: atelier.formation.k8s/v1
kind: Sauvegarde
metadata:
  name: hebdomadaire
  namespace: sauvegardes
spec:
  source: donnees-registre
  retentionJours: 14
---
apiVersion: atelier.formation.k8s/v1
kind: Sauvegarde
metadata:
  name: ancienne
  namespace: sauvegardes
  finalizers:
    - atelier.formation.k8s/archivage
spec:
  source: donnees-journal
  retentionJours: 90
YAML
kubectl -n sauvegardes delete sauvegarde ancienne --wait=false
test -n "$(kubectl -n sauvegardes get sauvegarde ancienne -o jsonpath='{.metadata.deletionTimestamp}')"

install -d -m 0755 /var/lib/dsoxlab
printf '{"crd_uid": "%s", "hebdomadaire_uid": "%s"}\n' \
  "$(kubectl get crd sauvegardes.atelier.formation.k8s -o jsonpath='{.metadata.uid}')" \
  "$(kubectl -n sauvegardes get sauvegarde hebdomadaire -o jsonpath='{.metadata.uid}')" > "$MEMOIRE"

rm -rf "${LAB_HOME:?}/sauvegardes"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/sauvegardes"
echo "Situation posée : CRD Sauvegarde, hebdomadaire à 14 jours, ancienne en Terminating."
