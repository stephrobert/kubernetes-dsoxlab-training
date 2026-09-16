#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
NS=equipe-dev
SUJET="system:serviceaccount:${NS}:dev-sa"

# 1. Reprendre le pouvoir. Le ClusterRoleBinding est un objet de CLUSTER : le
#    supprimer retire le droit partout d'un coup, y compris dans le namespace
#    de l'équipe. C'est voulu, on redonne juste après ce qu'il faut.
$K delete clusterrolebinding dev-admin-binding --ignore-not-found --wait=true

# 2. Rendre le strict nécessaire, et RIEN d'autre. Le Role vit dans le
#    namespace : ce qu'il accorde ne vaut que là, sans qu'on ait à l'écrire.
#
#    Les Secrets ne sont pas dans la liste, et c'est le point du lab. Les
#    Deployments appartiennent au groupe d'API « apps », les Pods et les
#    Services au groupe « core », qui s'écrit comme une chaîne vide.
cat <<'YAML' | $K apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: dev-role
  namespace: equipe-dev
rules:
  - apiGroups: [""]
    resources: ["pods", "services"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-role-binding
  namespace: equipe-dev
subjects:
  - kind: ServiceAccount
    name: dev-sa
    namespace: equipe-dev
roleRef:
  kind: Role
  name: dev-role
  apiGroup: rbac.authorization.k8s.io
YAML

# 3. La preuve, posée à l'API server au nom du compte lui-même. C'est la seule
#    façon de répondre à « que peut-il faire ? » sans relire les manifestes.
echo "--- ce qui doit rester permis ---"
for question in "list pods" "create deployments" "list services"; do
  # shellcheck disable=SC2086
  echo -n "can-i ${question} -n ${NS} : "
  $K auth can-i ${question} -n "$NS" --as="$SUJET"
done

echo "--- ce qui doit être refusé ---"
for question in "list secrets" "get secret/jeton-de-paiement"; do
  # shellcheck disable=SC2086
  echo -n "can-i ${question} -n ${NS} : "
  $K auth can-i ${question} -n "$NS" --as="$SUJET" || true
done
echo -n "can-i list pods -n kube-system : "
$K auth can-i list pods -n kube-system --as="$SUJET" || true
echo -n "can-i '*' '*' --all-namespaces : "
$K auth can-i '*' '*' --all-namespaces --as="$SUJET" || true

# 4. Et l'application, elle, tourne toujours.
$K -n "$NS" rollout status deployment/portail-dev --timeout=120s
echo "dev-sa travaille dans son namespace, et nulle part ailleurs."
