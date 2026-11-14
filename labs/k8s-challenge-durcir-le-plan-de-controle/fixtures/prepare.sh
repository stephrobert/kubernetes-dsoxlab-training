#!/usr/bin/env bash
# Pose la situation : un plan de contrôle kubeadm tel qu'il sort de
# l'installation, sans audit, et le compte d'échecs CIS de départ.
#
# Trois précautions, reprises des labs guidés cks-api-server-hardening,
# cks-cis-benchmark-remediate et cks-audit-log-policy :
#
#   1. Les sauvegardes des trois manifestes vivent dans /var/backups, JAMAIS
#      dans /etc/kubernetes/manifests : le kubelet lancerait la copie comme un
#      second Pod statique, sur le même port.
#   2. Les manifestes sont RESTAURÉS au début de chaque passage. Sans cela, un
#      second run après un travail réussi partirait d'un plan de contrôle déjà
#      durci, et le challenge rendrait 100 avant tout travail.
#   3. Le journal et la politique d'audit d'un passage précédent sont retirés :
#      le dernier test cherche une trace écrite PENDANT la session.
#
# Ce que ce script ajoute : il relance kube-bench lui-même, sur le plan de
# contrôle restauré, et range le nombre d'échecs sur le nœud. Le test compare
# à ce nombre mesuré, jamais à un nombre écrit en dur : kube-bench ajoute des
# contrôles à chaque version de son référentiel.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne rend que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

MANIFESTES=/etc/kubernetes/manifests
ETAT=/var/lib/dsoxlab/k8s-challenge-durcir-le-plan-de-controle
DEPART="${ETAT}/echecs-au-depart"
mkdir -p /var/backups "$ETAT"
chmod 0700 "$ETAT"

attendre_le_plan_de_controle() {
  # Deux attentes : /healthz répond avant que les Pods statiques ne soient
  # revenus Running, et le validateur photographie le cluster dans cette
  # fenêtre.
  for _ in $(seq 1 60); do
    kubectl get --raw /healthz >/dev/null 2>&1 && break
    sleep 3
  done
  kubectl get --raw /healthz >/dev/null 2>&1 || {
    echo "L'API server ne répond plus après la restauration des manifestes." >&2
    return 1
  }
  for _ in $(seq 1 40); do
    phases=$(kubectl -n kube-system get pods -l tier=control-plane \
      -o jsonpath='{.items[*].status.phase}' 2>/dev/null || true)
    [[ -n "$phases" && "$phases" != *Pending* ]] && return 0
    sleep 3
  done
  echo "Le plan de contrôle ne revient pas en Running." >&2
  return 1
}

restaure=non
for composant in kube-apiserver kube-controller-manager kube-scheduler; do
  sauvegarde="/var/backups/${composant}.avant-durcir-plan.yaml"
  if [[ -f "$sauvegarde" ]]; then
    # On ne copie que si le fichier a changé : une copie identique ne
    # redémarre rien, mais elle ferait attendre pour rien.
    if ! cmp -s "$sauvegarde" "${MANIFESTES}/${composant}.yaml"; then
      cp -f "$sauvegarde" "${MANIFESTES}/${composant}.yaml"
      restaure=oui
    fi
  else
    cp -f "${MANIFESTES}/${composant}.yaml" "$sauvegarde"
  fi
done
if [[ "$restaure" == oui ]]; then
  # Le kubelet met quelques secondes à voir le fichier changé : sans cette
  # pause, l'attente qui suit lirait l'ancien Pod, encore Running.
  sleep 20
fi
attendre_le_plan_de_controle

rm -f /var/log/kubernetes/audit.log
rm -f /etc/kubernetes/audit-policy.yaml
rm -f "$DEPART"

grep -q -- "--audit-policy-file" "${MANIFESTES}/kube-apiserver.yaml" && {
  echo "Le manifeste porte déjà un audit : la restauration n'a pas marché." >&2
  exit 1
}
grep -q -- "--profiling=false" "${MANIFESTES}/kube-apiserver.yaml" && {
  echo "Le manifeste porte déjà --profiling=false : la restauration n'a pas marché." >&2
  exit 1
}

# Le namespace du challenge porte l'audit kube-bench et le Secret que l'audit
# de l'API server doit tracer.
if [[ "$(kubectl get namespace conformite -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/conformite --timeout=180s
fi
kubectl get namespace conformite >/dev/null 2>&1 || kubectl create namespace conformite

kubectl -n conformite delete secret jeton-de-paiement --ignore-not-found --wait=true
kubectl -n conformite create secret generic jeton-de-paiement \
  --from-literal=jeton="ce-que-l-audit-doit-tracer"

# Le profileur doit être OUVERT au départ, sinon l'état 2 ne mesure rien.
kubectl get --raw /debug/pprof/ >/dev/null 2>&1 || {
  echo "Le profileur est déjà fermé : le socle a changé, le challenge ne s'applique plus." >&2
  exit 1
}

# L'audit de départ, joué ICI sur le plan de contrôle restauré. L'image est
# tirée d'abord : sans elle, le premier audit passerait sa minute à la
# télécharger.
crictl pull aquasec/kube-bench:v0.16.0@sha256:75506f222d1eb6ce2a751a5533bdc0a3b54c898e2e49e7751d0ee22cfb862679 >/dev/null 2>&1 || true
kubectl -n conformite delete job kube-bench --ignore-not-found --cascade=foreground --wait=true
kubectl apply -f /root/kube-bench-job.yaml
kubectl -n conformite wait --for=condition=complete job/kube-bench --timeout=300s
pod=$(kubectl -n conformite get pods -l job-name=kube-bench -o jsonpath='{.items[0].metadata.name}')
kubectl -n conformite logs "$pod" > "${ETAT}/audit-de-depart.json"

python3 - "${ETAT}/audit-de-depart.json" "$DEPART" <<'PY'
import json
import sys

brut = open(sys.argv[1], encoding="utf-8").read()
debut = brut.find("{")
if debut < 0:
    sys.exit("La sortie de kube-bench ne contient pas de JSON.")
rapport = json.loads(brut[debut:])
total = sum(int(c.get("total_fail", 0)) for c in rapport.get("Controls", []))
etats = {
    str(r.get("test_number")): str(r.get("status"))
    for c in rapport.get("Controls", [])
    for g in c.get("tests", [])
    for r in g.get("results", [])
}
vises = ("1.2.15", "1.3.2", "1.4.1")
passes = [v for v in vises if etats.get(v) == "PASS"]
if passes:
    sys.exit(f"Ces contrôles visés passent déjà au départ : {passes}. Le socle a changé.")
if total <= 0:
    sys.exit("kube-bench ne compte aucun échec au départ : l'état 4 ne mesurerait rien.")
with open(sys.argv[2], "w", encoding="utf-8") as f:
    f.write(f"{total}\n")
print(f"Échecs CIS au départ : {total}")
PY
chmod 0600 "$DEPART"

# Le Job de départ est retiré : l'apprenant lance le sien, et le test aussi.
kubectl -n conformite delete job kube-bench --ignore-not-found --cascade=foreground --wait=true

echo "Situation posée : plan de contrôle d'origine, aucun audit, $(cat "$DEPART") échecs CIS au départ."
