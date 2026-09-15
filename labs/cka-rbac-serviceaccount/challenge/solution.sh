#!/usr/bin/env bash
# Solution du formateur. Rejouée sur le control plane après `dsoxlab run`,
# elle prouve que le lab est FAISABLE et que ses tests passent quand le
# travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Le diagnostic : pas de Pod, et l'event du ReplicaSet dit pourquoi.
$K -n app-team get deployment inventaire
$K -n app-team get events --field-selector reason=FailedCreate -o jsonpath='{.items[-1].message}{"\n"}' || true

# 2. L'identité, le droit, le lien. Le sujet du RoleBinding est le
#    ServiceAccount, pas un utilisateur.
$K -n app-team create serviceaccount pod-reader
$K -n app-team create role pod-reader-role --verb=get,list,watch --resource=pods
$K -n app-team create rolebinding pod-reader-binding \
  --role=pod-reader-role --serviceaccount=app-team:pod-reader

# 3. Le ReplicaSet réessaie de lui-même dès que le ServiceAccount existe.
$K -n app-team rollout status deployment/inventaire --timeout=180s

# 4. La preuve, depuis le Pod, avec son jeton : lister passe, le reste non.
$K auth can-i list pods -n app-team --as system:serviceaccount:app-team:pod-reader
$K auth can-i delete pods -n app-team --as system:serviceaccount:app-team:pod-reader || true
$K -n app-team exec deploy/inventaire -- sh -c '
  D=/var/run/secrets/kubernetes.io/serviceaccount
  A="https://kubernetes.default.svc/api/v1"
  H="Authorization: Bearer $(cat $D/token)"
  echo "lister les pods d app-team : $(curl -s -o /dev/null -w "%{http_code}" --cacert $D/ca.crt -H "$H" $A/namespaces/app-team/pods)"
  echo "lire les secrets d app-team : $(curl -s -o /dev/null -w "%{http_code}" --cacert $D/ca.crt -H "$H" $A/namespaces/app-team/secrets)"
  echo "lister les pods de default : $(curl -s -o /dev/null -w "%{http_code}" --cacert $D/ca.crt -H "$H" $A/namespaces/default/pods)"
'
echo "inventaire tourne sous pod-reader et ne peut que lire les Pods de son namespace."
