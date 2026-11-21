#!/usr/bin/env bash
# Pose la partie « API server » du challenge sur k8s-cp.lab : l'anonyme est
# accepté partout (réglage par défaut de kubeadm, qui lui laisse /version), et
# une ClusterRoleBinding « annuaire-public » lui donne en plus le rôle view.
#
# Précautions reprises de cks-restreindre-l-acces-anonyme :
#   - la sauvegarde du manifeste vit dans /var/backups, JAMAIS dans
#     /etc/kubernetes/manifests, que le kubelet surveille ;
#   - tout est RESTAURÉ au début de chaque passage, sinon un second run après
#     un travail réussi partirait d'un API server déjà fermé.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare-api.log) 2>&1
set -x

MANIFESTE=/etc/kubernetes/manifests/kube-apiserver.yaml
SAUVEGARDE=/var/backups/kube-apiserver.avant-durcir-les-noeuds.yaml

attendre_l_api() {
  for _ in $(seq 1 60); do
    kubectl get --raw /healthz >/dev/null 2>&1 && break
    sleep 3
  done
  kubectl get --raw /healthz >/dev/null 2>&1 || {
    echo "L API server ne repond plus apres restauration du manifeste." >&2
    return 1
  }
  for _ in $(seq 1 40); do
    phases=$(kubectl -n kube-system get pods -l component=kube-apiserver \
      -o jsonpath='{.items[*].status.phase}' 2>/dev/null || true)
    [[ -n "$phases" && "$phases" != *Pending* ]] && return 0
    sleep 3
  done
  echo "Le Pod statique kube-apiserver ne revient pas en Running." >&2
  return 1
}

mkdir -p /var/backups

# 1. Partir de l'état d'origine
[[ -f "$SAUVEGARDE" ]] || cp -f "$MANIFESTE" "$SAUVEGARDE"
if grep -q -- '--authentication-config' "$SAUVEGARDE"; then
  echo "La sauvegarde du manifeste porte deja --authentication-config : le socle a change." >&2
  exit 1
fi
if ! cmp -s "$SAUVEGARDE" "$MANIFESTE"; then
  install -m 0600 "$SAUVEGARDE" "$MANIFESTE"
  # Le kubelet met quelques secondes à voir le manifeste changé : /healthz
  # répond encore par l'ANCIEN Pod (mesuré le 2026-11-17 dans le lab guidé).
  sleep 20
fi
rm -f /etc/kubernetes/authn-config.yaml
attendre_l_api

# 2. Une lecture publique de plus
kubectl delete clusterrolebinding annuaire-public --ignore-not-found
kubectl create clusterrolebinding annuaire-public --clusterrole=view --user=system:anonymous

# 3. La porte doit être OUVERTE, sinon le challenge ne mesure rien
code_version=$(curl -sk -o /dev/null -w '%{http_code}' https://127.0.0.1:6443/version)
code_pods=$(curl -sk -o /dev/null -w '%{http_code}' https://127.0.0.1:6443/api/v1/namespaces/default/pods)
[[ "$code_version" == 200 && "$code_pods" == 200 ]] || {
  echo "Situation non posee : /version $code_version, pods $code_pods (200 attendus)." >&2
  exit 1
}
echo "API server ouvert a l anonyme, lecture publique posee."
