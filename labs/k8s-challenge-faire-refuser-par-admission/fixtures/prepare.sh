#!/usr/bin/env bash
# Pose la situation : quatre namespaces, et un cluster qui admet tout.
#
#   - vitrine    : aucun standard de sécurité, c'est là que va le Pod conforme ;
#   - paiement   : le Pod privilégié caisse, cinq défauts cumulés, repris du
#                  lab guidé cks-secure-existing-pod ;
#   - production : un Pod épinglé par son digest, repris du lab guidé
#                  cks-validating-admission-policy, qui ne doit pas tomber ;
#   - recette    : le témoin. Rien n'y est posé : une image par tag doit y
#                  passer avant comme après le travail.
#
# Tout ce que l'apprenant produit est retiré s'il traîne d'un passage
# précédent, politiques d'admission et labels de standard compris : sans cela,
# le challenge rendrait des points avant tout travail.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne rend que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

# Les politiques d'admission d'un passage précédent. « safe-upgrades » est
# une politique du socle, que les labs guidés épargnent aussi.
kubectl get validatingadmissionpolicybinding -o name 2>/dev/null \
  | grep -vE 'safe-upgrades' | xargs -r kubectl delete --ignore-not-found || true
kubectl get validatingadmissionpolicy -o name 2>/dev/null \
  | grep -vE 'safe-upgrades' | xargs -r kubectl delete --ignore-not-found || true

for ns in vitrine paiement production recette; do
  if [[ "$(kubectl get namespace "$ns" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
    kubectl wait --for=delete "namespace/$ns" --timeout=180s
  fi
done
kubectl get namespace vitrine >/dev/null 2>&1 || kubectl create namespace vitrine
kubectl get namespace paiement >/dev/null 2>&1 || kubectl create namespace paiement
kubectl get namespace production >/dev/null 2>&1 || kubectl create namespace production
kubectl get namespace recette >/dev/null 2>&1 || kubectl create namespace recette

# vitrine repart SANS aucun label de standard, et sans le Pod demandé.
for mode in enforce warn audit; do
  kubectl label namespace vitrine "pod-security.kubernetes.io/${mode}-" >/dev/null 2>&1 || true
  kubectl label namespace vitrine "pod-security.kubernetes.io/${mode}-version-" >/dev/null 2>&1 || true
done
kubectl -n vitrine delete pod catalogue --ignore-not-found --wait=true

# paiement : le Pod de remplacement retiré, l'original reposé.
kubectl -n paiement delete pod caisse-durcie caisse --ignore-not-found --wait=true
kubectl apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: caisse
  namespace: paiement
  labels:
    app: caisse
spec:
  # Défaut 1 : le Pod partage le namespace de processus du NŒUD.
  hostPID: true
  containers:
    - name: caisse
      # Défaut 2 : un tag flottant.
      image: busybox:latest
      command: ["sh", "-c", "sleep 86400"]
      securityContext:
        # Défaut 3 : conteneur privilégié.
        privileged: true
        # Défaut 4 : exécution en root.
        runAsUser: 0
        # Défaut 5 : l'escalade de privilèges reste possible.
        allowPrivilegeEscalation: true
YAML

# production : l'application épinglée qui doit survivre à la politique.
kubectl -n production delete pod conforme --ignore-not-found --wait=true
kubectl apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: conforme
  namespace: production
spec:
  containers:
    - name: appli
      image: busybox@sha256:ab33eacc8251e3807b85bb6dba570e4698c3998eca6f0fc2ccb60575a563ea74
      command: ["sh", "-c", "sleep 86400"]
YAML

kubectl -n paiement wait --for=condition=ready pod/caisse --timeout=300s
kubectl -n production wait --for=condition=ready pod/conforme --timeout=300s

# Les images des sondes sont tirées maintenant sur les deux nœuds par le
# kubelet, au fil des Pods ; busybox:1.37 l'est ici sur le plan de contrôle,
# pour que le premier essai de l'apprenant ne passe pas sa minute à la tirer.
crictl pull busybox:1.37 >/dev/null 2>&1 || true

echo "Situation posée : vitrine sans standard, caisse privilégié, production et recette sans politique."
