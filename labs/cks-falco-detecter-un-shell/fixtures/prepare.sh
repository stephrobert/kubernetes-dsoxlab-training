#!/usr/bin/env bash
# Pose la situation : Falco tourne sur k8s-cp.lab sans aucune règle
# personnalisée, et écrit ses alertes en JSON dans un fichier. Le namespace
# protégé paiements porte le Pod caisse ; le namespace accueil porte le Pod
# vitrine, hors du périmètre. Les deux Pods sont sur k8s-cp.lab : Falco ne
# regarde que ce nœud.
#
# L'installation de Falco est celle de k8s-challenge-confiner-et-detecter,
# validée : paquet officiel épinglé, pilote modern_ebpf, falcoctl masqué pour
# que falco_rules.yaml ne bouge pas dans le dos du correcteur.
#
# Rejouable : les règles fournies sont rétablies si elles ont été touchées,
# rules.d est vidé, le journal remis à zéro, les deux namespaces recréés.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

# Falco épinglé, depuis le dépôt officiel falcosecurity : 0.45.2, la version
# que le challenge du niveau 5 a validée le 2026-11-14.
FALCO_VERSION=0.45.2
FALCO_JOURNAL=/var/log/falco/events.json
IMAGE='nginx:1.27@sha256:6784fb0834aa7dbbe12e3d7471e69c290df3e6ba810dc38b34ae33d3c1c05f7d'

installer_falco() {
  FALCO_FRONTEND=noninteractive FALCO_DRIVER_CHOICE=modern_ebpf FALCOCTL_ENABLED=no \
  DEBIAN_FRONTEND=noninteractive \
    apt-get install -y -qq -o DPkg::Lock::Timeout=300 "$@" "falco=${FALCO_VERSION}"
}

if [[ "$(dpkg-query -W -f='${Status} ${Version}' falco 2>/dev/null)" != "install ok installed ${FALCO_VERSION}" ]]; then
  install -d -m 0755 /usr/share/keyrings
  curl -fsSL https://falco.org/repo/falcosecurity-packages.asc \
    | gpg --dearmor --yes -o /usr/share/keyrings/falco-archive-keyring.gpg
  echo "deb [signed-by=/usr/share/keyrings/falco-archive-keyring.gpg] https://download.falco.org/packages/deb stable main" \
    > /etc/apt/sources.list.d/falcosecurity.list
  apt-get update -qq -o DPkg::Lock::Timeout=300
  installer_falco
fi

# Les règles FOURNIES sont remises d'origine si un passage précédent les a
# touchées : le paquet en garde l'empreinte.
attendu=$(awk '$2 == "etc/falco/falco_rules.yaml" {print $1}' /var/lib/dpkg/info/falco.md5sums)
if [[ -z "$attendu" ]] || [[ "$(md5sum /etc/falco/falco_rules.yaml 2>/dev/null | cut -d' ' -f1)" != "$attendu" ]]; then
  installer_falco --reinstall
fi

# Aucune règle personnalisée.
printf '%s\n' '# Your custom rules!' > /etc/falco/falco_rules.local.yaml
rm -rf /etc/falco/rules.d
install -d -m 0755 /etc/falco/rules.d

# La sortie que le correcteur lit : du JSON, une alerte par ligne, dans un
# fichier. La sortie standard du service part dans /dev/null.
install -d -m 0750 /var/log/falco
: > "$FALCO_JOURNAL"
cat > /etc/falco/config.d/zz-dsoxlab-sortie-json.yaml <<YAML
json_output: true
file_output:
  enabled: true
  keep_alive: false
  filename: ${FALCO_JOURNAL}
YAML

attendre_falco() {
  for _ in $(seq 1 40); do
    if systemctl is-active --quiet falco-modern-bpf.service \
       && curl -fsS http://127.0.0.1:8765/healthz >/dev/null 2>&1; then
      return 0
    fi
    sleep 3
  done
  echo "Falco ne repond pas. Journal du service :" >&2
  journalctl -u falco-modern-bpf.service -n 60 --no-pager >&2 || true
  return 1
}
systemctl enable falco-modern-bpf.service
systemctl restart falco-modern-bpf.service
attendre_falco

for ns in paiements accueil; do
  if [[ "$(kubectl get namespace "$ns" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
    kubectl wait --for=delete "namespace/$ns" --timeout=180s
  fi
  kubectl delete namespace "$ns" --ignore-not-found --wait=true
  kubectl create namespace "$ns"
done

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata: {name: caisse, namespace: paiements, labels: {app: caisse}}
spec:
  nodeSelector: {kubernetes.io/hostname: k8s-cp.lab}
  containers:
  - name: app
    image: $IMAGE
---
apiVersion: v1
kind: Pod
metadata: {name: vitrine, namespace: accueil, labels: {app: vitrine}}
spec:
  nodeSelector: {kubernetes.io/hostname: k8s-cp.lab}
  containers:
  - name: app
    image: $IMAGE
EOF
kubectl -n paiements wait --for=condition=Ready pod/caisse --timeout=180s
kubectl -n accueil wait --for=condition=Ready pod/vitrine --timeout=180s

echo "Situation posée : Falco tourne sans règle personnalisée, caisse et vitrine sont prêts sur k8s-cp.lab."
