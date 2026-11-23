#!/usr/bin/env bash
# Pose la situation du lab k8s-valider-et-modifier-a-l-admission.
#
#   - le namespace ateliers, ou plus aucun Pod ne se cree : un webhook de
#     validation controle-ateliers, en failurePolicy Fail, appelle le Service
#     verificateur du namespace ateliers-outils, qui n'a aucun Pod derriere
#     lui (le controleur a ete desinstalle, sa configuration est restee) ;
#   - le namespace ateliers-temoin, qui sert a verifier que les regles du
#     candidat ne debordent pas d'ateliers.
#
# Etat de depart releve le 2026-11-23 sur kubeadm v1.37.2 : la creation d'un
# Pod dans ateliers echoue en « failed calling webhook ... connection refused ».
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

# Ce que le candidat doit produire est retire s'il traine d'un passage
# precedent : sans cela, le lab rendrait 100 avant le travail. La liaison
# d'abord, la politique ensuite. Les politiques safe-upgrades viennent des CRD
# de la Gateway API, installees par un autre lab : on n'y touche pas.
kubectl get mutatingadmissionpolicybinding -o name 2>/dev/null \
  | xargs -r kubectl delete --ignore-not-found || true
kubectl get mutatingadmissionpolicy -o name 2>/dev/null \
  | xargs -r kubectl delete --ignore-not-found || true
kubectl get validatingadmissionpolicybinding -o name 2>/dev/null \
  | grep -vE 'safe-upgrades' | xargs -r kubectl delete --ignore-not-found || true
kubectl get validatingadmissionpolicy -o name 2>/dev/null \
  | grep -vE 'safe-upgrades' | xargs -r kubectl delete --ignore-not-found || true

for ns in ateliers ateliers-temoin ateliers-outils; do
  if [[ "$(kubectl get namespace "$ns" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
    kubectl wait --for=delete "namespace/$ns" --timeout=180s
  fi
  kubectl get namespace "$ns" >/dev/null 2>&1 || kubectl create namespace "$ns"
done

# Le Service du controleur desinstalle : il existe, mais aucun Pod ne porte
# son selecteur, donc il n'a aucun endpoint.
kubectl apply -f - <<'YAML'
apiVersion: v1
kind: Service
metadata:
  name: verificateur
  namespace: ateliers-outils
spec:
  selector:
    app: verificateur
  ports:
    - port: 443
      targetPort: 8443
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: controle-ateliers
webhooks:
  - name: controle.ateliers-outils.svc
    clientConfig:
      service:
        name: verificateur
        namespace: ateliers-outils
        path: /valider
    rules:
      - apiGroups: [""]
        apiVersions: [v1]
        operations: [CREATE, UPDATE]
        resources: [pods]
    namespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: ateliers
    admissionReviewVersions: [v1]
    sideEffects: None
    failurePolicy: Fail
YAML

# On montre l'etat de depart dans le journal : aucun Pod ne passe.
sleep 3
if kubectl -n ateliers run sonde-depart --image=busybox:1.37 --restart=Never \
  --dry-run=server -- sleep 5; then
  echo "Situation NON posee : un Pod passe encore dans ateliers." >&2
  exit 1
fi
echo "Situation posee : le webhook controle-ateliers bloque les Pods d'ateliers."
