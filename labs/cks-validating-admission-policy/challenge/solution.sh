#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -eu

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Constater l'état de départ : une image par tag passe.
echo -n "avant, une image par tag : "
$K -n production run sonde-avant --image=busybox:1.37 --restart=Never \
  --command -- sh -c 'sleep 5' >/dev/null 2>&1 \
  && { echo "acceptée"; $K -n production delete pod sonde-avant --ignore-not-found >/dev/null; } \
  || echo "refusée"

# 2. La politique. Elle est évaluée PAR L'API SERVER, en CEL : rien à
#    installer, rien à maintenir en vie. Un webhook rendrait le même service,
#    mais sa panne bloquerait toute création de Pod tant que sa failurePolicy
#    vaut Fail.
#
#    `object.spec.containers.all(c, …)` exige que TOUS les conteneurs
#    satisfassent la condition : `exists` n'exigerait qu'un seul, ce qui
#    laisserait passer un Pod dont un conteneur sur deux est épinglé.
cat <<'YAML' | $K apply -f -
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: image-epinglee
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: ["v1"]
        operations: ["CREATE", "UPDATE"]
        resources: ["pods"]
  validations:
    - expression: "object.spec.containers.all(c, c.image.contains('@sha256:'))"
      message: "toute image doit etre epinglee par son digest"
YAML

# 3. La liaison. Une politique SANS liaison n'agit sur rien : c'est elle qui
#    dit OÙ la politique s'applique, et ce qu'on fait des violations.
#    `validationActions: [Deny]` refuse ; `Warn` ou `Audit` laisseraient
#    passer en se contentant de signaler.
cat <<'YAML' | $K apply -f -
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: image-epinglee
spec:
  policyName: image-epinglee
  validationActions: [Deny]
  matchResources:
    namespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: production
YAML

# L'API server recharge ses politiques après notification.
sleep 10

# 4. La preuve, dans les deux sens.
echo -n "après, une image par tag : "
$K -n production run sonde-tag --image=busybox:1.37 --restart=Never \
  --command -- sh -c 'sleep 5' >/dev/null 2>&1 \
  && { echo "ACCEPTÉE, anormal"; $K -n production delete pod sonde-tag --ignore-not-found >/dev/null; } \
  || echo "refusée"
echo -n "après, une image épinglée : "
$K -n production run sonde-digest --image=busybox@sha256:ab33eacc8251e3807b85bb6dba570e4698c3998eca6f0fc2ccb60575a563ea74 --restart=Never \
  --command -- sh -c 'sleep 5' >/dev/null 2>&1 \
  && { echo "acceptée"; $K -n production delete pod sonde-digest --ignore-not-found --wait=false >/dev/null; } \
  || echo "REFUSÉE, anormal"
echo -n "l'application du namespace tourne toujours : "
$K -n production get pod conforme -o jsonpath='{.status.phase}'; echo
