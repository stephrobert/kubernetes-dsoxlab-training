#!/usr/bin/env bash
# Défait l'épreuve k8s-epreuve-securiser-un-cluster, que l'apprenant ait réussi
# ou non. Appelé par cleanup.yaml.
#
# Les noms des profils, des fichiers d'audit et des objets de cluster sont
# libres : on les LIT sur le cluster et sur le nœud avant de retirer quoi que
# ce soit, puis on rend le plan de contrôle tel que kubeadm l'avait écrit.
#
# Chaque étape tolère l'échec et passe à la suivante : un nettoyage qui
# s'arrête à la première erreur laisse le cluster à moitié durci, et c'est le
# lab suivant qui le paie.
set -uo pipefail
exec > >(tee /var/log/dsoxlab-cleanup.log) 2>&1
set -x

ETAT=/var/lib/dsoxlab/epreuve-securiser-un-cluster
MANIFESTES=/etc/kubernetes/manifests
COMPOSANTS=(kube-apiserver kube-controller-manager kube-scheduler)
NAMESPACES=(boutique facturation commandes partenaires paiement registre conformite)

# 1. Ce que les Pods de facturation déclarent, avant de les retirer.
lire_profils() {
  kubectl -n facturation get pod "$1" -o json 2>/dev/null | python3 -c '
import json, sys
champ = sys.argv[1]
p = json.load(sys.stdin)["spec"]
c = [p.get("securityContext") or {}] + [x.get("securityContext") or {} for x in p["containers"]]
print(" ".join(sorted({(s.get(champ) or {}).get("localhostProfile", "") for s in c} - {""})))
' "$2" 2>/dev/null || true
}
for nom in $(lire_profils consultation appArmorProfile); do
  printf '%s' "$nom" > /sys/kernel/security/apparmor/.remove 2>/dev/null || true
  { grep -lsE "^[[:space:]]*profile[[:space:]]+${nom}([[:space:]]|\{|$)" /etc/apparmor.d/* || true; } | xargs -r rm -f
done
for chemin in $(lire_profils numerotation seccompProfile); do
  [[ "$chemin" == *..* ]] || rm -f "/var/lib/kubelet/seccomp/${chemin}"
done

# 2. Les fichiers d'audit que l'API server désigne, lus AVANT de restaurer son
#    manifeste : la politique et le journal ont le chemin que l'apprenant a
#    choisi.
audit_fichiers=$(grep -oE -- '--audit-(policy-file|log-path)=[^"[:space:]]+' "${MANIFESTES}/kube-apiserver.yaml" 2>/dev/null \
  | cut -d= -f2- || true)

# 3. Les espaces de l'épreuve.
kubectl delete namespace "${NAMESPACES[@]}" --ignore-not-found --wait=true --timeout=300s || true

# 4. Les objets de cluster créés pendant l'épreuve : tout ce qui n'était pas
#    là au relevé du setup.
noms() { kubectl get "$1" -o name 2>/dev/null | sort; }
for type in validatingadmissionpolicybindings validatingadmissionpolicies runtimeclasses; do
  if [[ -f "${ETAT}/${type}.avant" ]]; then
    comm -13 "${ETAT}/${type}.avant" <(noms "$type") | xargs -r kubectl delete --ignore-not-found --wait=true || true
  fi
done

# 5. Istio en entier, et les ConfigMaps istio-ca-* qu'istiod sème dans chaque
#    namespace (relevé de cks-istio-mtls-lockdown).
istioctl uninstall --purge -y || true
kubectl delete namespace istio-system --ignore-not-found --wait=true --timeout=180s || true
kubectl get namespace -o name | sed 's|namespace/||' | while read -r ns; do
  kubectl get configmap -n "$ns" -o name 2>/dev/null \
    | grep -E '^configmap/istio-ca-' \
    | xargs -r kubectl delete -n "$ns" --ignore-not-found >/dev/null || true
done

# 6. Le plan de contrôle, tel que kubeadm l'avait écrit. On attend que chaque
#    Pod statique restauré ait changé d'empreinte, puis qu'il soit prêt : juste
#    après la copie, le Pod miroir montre encore l'ancien conteneur Running
#    (relevé de cks-cis-benchmark-remediate du 2026-11-12).
empreinte() {
  kubectl -n kube-system get pod "$1-k8s-cp.lab" \
    -o jsonpath='{.metadata.annotations.kubernetes\.io/config\.hash}' 2>/dev/null || true
}
declare -A avant
restaures=()
for composant in "${COMPOSANTS[@]}"; do
  sauvegarde="/var/backups/${composant}.avant-epreuve-n5.yaml"
  [[ -f "$sauvegarde" ]] || continue
  if ! cmp -s "$sauvegarde" "${MANIFESTES}/${composant}.yaml"; then
    avant[$composant]=$(empreinte "$composant")
    cp -f "$sauvegarde" "${MANIFESTES}/${composant}.yaml"
    restaures+=("$composant")
  fi
done
for _ in $(seq 1 60); do
  kubectl get --raw /healthz >/dev/null 2>&1 && break
  sleep 3
done
for composant in "${restaures[@]}"; do
  for _ in $(seq 1 60); do
    e=$(empreinte "$composant")
    pret=$(kubectl -n kube-system get pod "${composant}-k8s-cp.lab" \
      -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || true)
    [[ -n "$e" && "$e" != "${avant[$composant]}" && "$pret" == "True" ]] && break
    sleep 3
  done
done
for _ in $(seq 1 40); do
  phases=$(kubectl -n kube-system get pods -l tier=control-plane \
    -o jsonpath='{.items[*].status.phase}' 2>/dev/null || true)
  [[ -n "$phases" && "$phases" != *Pending* ]] && break
  sleep 3
done
for chemin in $audit_fichiers; do
  case "$chemin" in
    /etc/kubernetes/manifests/*|/etc/kubernetes/pki/*|/etc/kubernetes/*.conf) ;;
    /*) rm -f "$chemin" ;;
  esac
done
# Les sauvegardes ne sont retirées que si l'API répond : sans elles, un plan de
# contrôle mal restauré ne pourrait plus l'être. Gardées à tort, elles
# ramèneraient au prochain setup des manifestes qu'un autre lab (une montée de
# version kubeadm) aurait légitimement changés.
if kubectl get --raw /healthz >/dev/null 2>&1; then
  for composant in "${COMPOSANTS[@]}"; do
    rm -f "/var/backups/${composant}.avant-epreuve-n5.yaml"
  done
fi

# 7. Falco purgé : il tourne en permanence et coûte de la mémoire au plan de
#    contrôle, que les labs suivants n'ont pas à payer.
systemctl stop falco-modern-bpf.service || true
DEBIAN_FRONTEND=noninteractive apt-get purge -y -qq -o DPkg::Lock::Timeout=300 falco || true
rm -rf /etc/falco /var/log/falco /etc/apt/sources.list.d/falcosecurity.list \
  /usr/share/keyrings/falco-archive-keyring.gpg

# 8. Le répertoire du catalogue (Dockerfile, clés de signature) et le relevé.
rm -rf /root/boutique "$ETAT"

echo "Epreuve defaite."
