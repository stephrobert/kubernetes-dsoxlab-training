#!/usr/bin/env bash
# Pose la situation du lab cks-restreindre-l-acces-anonyme sur k8s-cp.lab :
# trois portes ouvertes aux clients sans identifiant.
#
#   1. L'API server tourne SANS le plugin d'admission NodeRestriction (la
#      ligne --enable-admission-plugins=NodeRestriction de kubeadm est retirée).
#   2. Une ClusterRoleBinding « lecture-publique » donne le rôle view au groupe
#      system:unauthenticated : tout client anonyme lit les objets du cluster.
#   3. Le kubelet du control plane accepte l'anonyme (anonymous.enabled: true)
#      et autorise tout (authorization.mode: AlwaysAllow).
#
# Mêmes précautions que cks-api-server-hardening :
#   - les sauvegardes vivent dans /var/backups, JAMAIS dans
#     /etc/kubernetes/manifests, que le kubelet surveille ;
#   - tout est RESTAURÉ au début de chaque passage, sinon un second run après
#     un travail réussi partirait d'un nœud déjà fermé.
#
# État de départ relevé le 2026-11-17 sur kubeadm v1.37.2 : NodeRestriction
# actif, kubelet en anonymous.enabled: false et mode Webhook (401 anonyme sur
# 10250), deux liaisons seulement vers les anonymes (system:public-info-viewer,
# et kubeadm:bootstrap-signer-clusterinfo dans kube-public).
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

MANIFESTE=/etc/kubernetes/manifests/kube-apiserver.yaml
SAUVEGARDE=/var/backups/kube-apiserver.avant-acces-anonyme.yaml
KUBELET=/var/lib/kubelet/config.yaml
SAUVEGARDE_KUBELET=/var/backups/kubelet-config.avant-acces-anonyme.yaml

attendre_l_api() {
  for _ in $(seq 1 60); do
    kubectl get --raw /healthz >/dev/null 2>&1 && break
    sleep 3
  done
  kubectl get --raw /healthz >/dev/null 2>&1 || {
    echo "L API server ne repond plus apres modification du manifeste." >&2
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

attendre_le_noeud() {
  for _ in $(seq 1 40); do
    [[ "$(kubectl get node k8s-cp.lab -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null)" == True ]] && return 0
    sleep 3
  done
  echo "k8s-cp.lab ne revient pas Ready apres le redemarrage du kubelet." >&2
  return 1
}

mkdir -p /var/backups

# 1. Partir de l'état d'origine
[[ -f "$SAUVEGARDE" ]] || cp -f "$MANIFESTE" "$SAUVEGARDE"
[[ -f "$SAUVEGARDE_KUBELET" ]] || cp -f "$KUBELET" "$SAUVEGARDE_KUBELET"
grep -q -- '--enable-admission-plugins=NodeRestriction' "$SAUVEGARDE" || {
  echo "La sauvegarde du manifeste n active pas NodeRestriction : le socle a change." >&2
  exit 1
}
rm -f /etc/kubernetes/authn-config.yaml
kubectl delete clusterrolebinding lecture-publique --ignore-not-found

# 2. API server sans NodeRestriction
grep -v -- '    - --enable-admission-plugins=NodeRestriction' "$SAUVEGARDE" > /root/kube-apiserver.lab.yaml
install -m 0600 /root/kube-apiserver.lab.yaml "$MANIFESTE"
rm -f /root/kube-apiserver.lab.yaml
# Le kubelet met quelques secondes à voir le manifeste changé : /healthz
# répond encore par l'ANCIEN Pod, puis l'API tombe pendant la recréation.
# Mesuré le 2026-11-17 : sans cette pause, l'attente concluait trop tôt et la
# vérification suivante trouvait l'API arrêtée.
sleep 20
attendre_l_api

# 3. Lecture publique
kubectl create clusterrolebinding lecture-publique --clusterrole=view --group=system:unauthenticated

# 4. Kubelet ouvert à l'anonyme
python3 - "$SAUVEGARDE_KUBELET" "$KUBELET" <<'PY'
import sys
import yaml
source, cible = sys.argv[1], sys.argv[2]
with open(source, encoding="utf-8") as f:
    conf = yaml.safe_load(f)
conf["authentication"]["anonymous"]["enabled"] = True
conf["authorization"]["mode"] = "AlwaysAllow"
with open(cible, "w", encoding="utf-8") as f:
    yaml.safe_dump(conf, f, sort_keys=False)
PY
systemctl restart kubelet
attendre_l_api
attendre_le_noeud

# 5. Les trois portes doivent être OUVERTES, sinon le lab ne mesure rien
code_pods=$(curl -sk -o /dev/null -w '%{http_code}' https://127.0.0.1:6443/api/v1/namespaces/default/pods)
code_kubelet=$(curl -sk -o /dev/null -w '%{http_code}' https://127.0.0.1:10250/pods)
[[ "$code_pods" == 200 && "$code_kubelet" == 200 ]] || {
  echo "Situation non posee : pods anonymes $code_pods, kubelet anonyme $code_kubelet (200 attendus)." >&2
  exit 1
}
if grep -q -- 'NodeRestriction' "$MANIFESTE"; then
  echo "NodeRestriction est encore dans le manifeste." >&2
  exit 1
fi
echo "Situation posee : NodeRestriction absent, lecture publique, kubelet ouvert."
