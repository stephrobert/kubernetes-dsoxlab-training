#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -eu

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Le plafond du namespace.
#
#    Un quota qui porte sur les `requests` rend INVALIDE tout Pod qui n'en
#    déclare pas : « must specify requests.cpu ». C'est logique, l'API ne peut
#    pas décompter ce qui n'est pas déclaré, mais cela transforme l'oubli d'un
#    développeur en refus incompréhensible. D'où le second objet.
cat <<'YAML' | $K apply -f -
apiVersion: v1
kind: ResourceQuota
metadata:
  name: plafond
  namespace: equipe-produit
spec:
  hard:
    requests.cpu: "2"
    requests.memory: 2Gi
    limits.cpu: "4"
    limits.memory: 4Gi
YAML

# 2. Les valeurs par défaut.
#
#    `default` alimente les limits, `defaultRequest` les requests. Un Pod qui
#    ne déclare rien reçoit donc les deux, et redevient décomptable par le
#    quota. C'est ce qui réconcilie le plafond et l'oubli.
cat <<'YAML' | $K apply -f -
apiVersion: v1
kind: LimitRange
metadata:
  name: valeurs-par-defaut
  namespace: equipe-produit
spec:
  limits:
    - type: Container
      default:
        cpu: 200m
        memory: 128Mi
      defaultRequest:
        cpu: 50m
        memory: 64Mi
YAML

# 3. La preuve, dans les deux sens.
echo -n "un Pod SANS requests est accepté : "
$K -n equipe-produit run sonde-sans --image=busybox:1.37 --restart=Never \
  --command -- sh -c 'sleep 30' >/dev/null 2>&1 && echo "oui" || echo "NON, anormal"
echo -n "  et il repart avec des requests : "
$K -n equipe-produit get pod sonde-sans \
  -o jsonpath='{.spec.containers[0].resources.requests.cpu}' 2>/dev/null; echo
$K -n equipe-produit delete pod sonde-sans --ignore-not-found --wait=false >/dev/null 2>&1

echo -n "un Pod demandant 64 CPU est refusé : "
$K -n equipe-produit run sonde-trop --image=busybox:1.37 --restart=Never \
  --overrides='{"spec":{"containers":[{"name":"x","image":"busybox:1.37","command":["sh","-c","sleep 5"],"resources":{"requests":{"cpu":"64","memory":"8Gi"},"limits":{"cpu":"64","memory":"8Gi"}}}]}}' \
  >/dev/null 2>&1 && { echo "NON, anormal"; $K -n equipe-produit delete pod sonde-trop --ignore-not-found >/dev/null; } \
  || echo "oui"

echo -n "l'application tourne toujours : "
$K -n equipe-produit get deployment catalogue -o jsonpath='{.status.readyReplicas}'; echo
