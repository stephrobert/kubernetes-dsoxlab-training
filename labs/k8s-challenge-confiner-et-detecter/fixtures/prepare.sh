#!/usr/bin/env bash
# Pose la situation du challenge k8s-challenge-confiner-et-detecter, fausse sur
# les seize états par construction :
#
#   - le nœud : containerd connaît runsc (gVisor), Falco tourne avec le pilote
#     modern_ebpf et écrit ses alertes en JSON, aucun profil AppArmor ni seccomp
#     du challenge n'existe, aucune règle personnalisée n'est chargée ;
#   - coffre : le namespace protégé, avec deux Pods fournis sur k8s-cp.lab,
#     tresor (le Pod protégé) et ordinaire (le témoin du runtime par défaut) ;
#   - maille : un maillage Istio en mode permissif, api et client-maille ;
#   - exterieur : client-nu (sans sidecar), curieux (le shell d'ailleurs, sur
#     k8s-cp.lab, là où Falco regarde) et vitrine (une cible hors de donnees) ;
#   - donnees : base, appli, intrus et annuaire, sans aucune politique réseau.
#
# Chaque brique reprend un lab attesté : cks-runtime-sandbox-gvisor,
# cks-istio-mtls-lockdown, cks-networkpolicy-default-deny,
# cks-apparmor-confiner-un-pod, cks-seccomp-profile. Falco est neuf.
#
# Rejouable : ce qu'un passage précédent a laissé est retiré avant d'être reposé.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne rend que
# « non-zero return code » quand ce script échoue, et le validateur relit ce
# fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

NOEUD=k8s-cp.lab
BUSYBOX=busybox:1.37
NGINX=nginx:1.27-alpine
PROFIL_APPARMOR=k8s-coffre-sans-tmp
PROFIL_SECCOMP=/var/lib/kubelet/seccomp/profiles/coffre-sans-chmod.json
RUNTIME_CLASS=gvisor-coffre

# gVisor épinglé sur une publication datée, et non sur « latest » : relevé le
# 2026-11-14 dans le dépôt officiel (storage.googleapis.com/gvisor), la
# publication 20261026.0 porte l'archive et son empreinte SHA-512.
GVISOR_VERSION=20261026.0
# Falco épinglé, depuis le dépôt officiel falcosecurity : 0.45.2 est la
# dernière version de l'index du dépôt le 2026-11-14.
FALCO_VERSION=0.45.2
FALCO_JOURNAL=/var/log/falco/events.json

attendre_l_api() {
  for _ in $(seq 1 60); do
    kubectl get --raw /healthz >/dev/null 2>&1 && return 0
    sleep 3
  done
  echo "L API server ne repond plus." >&2
  return 1
}

attendre_namespace_libre() {
  if [[ "$(kubectl get namespace "$1" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
    kubectl wait --for=delete "namespace/$1" --timeout=180s
  fi
}

# ---------------------------------------------------------------------------
# 1. gVisor, EN PREMIER : il redémarre containerd, ce qui ne doit arriver avant
#    qu'aucun Pod du challenge n'existe. Repris de cks-runtime-sandbox-gvisor,
#    ses quatre pièges de distribution compris (archive seule, bzip2 absent,
#    paquet Ubuntu périmé, répertoire gvisor-bin/ exigé par runsc).
# ---------------------------------------------------------------------------
CONF=/etc/containerd/config.toml
SAUVEGARDE=/var/backups/containerd.avant-gvisor.toml
mkdir -p /var/backups
[[ -f "$SAUVEGARDE" ]] || cp -f "$CONF" "$SAUVEGARDE"

if ! runsc --version 2>/dev/null | grep -c "release-${GVISOR_VERSION}" >/dev/null \
   || [[ ! -x /usr/local/bin/containerd-shim-runsc-v1 ]] \
   || [[ ! -x /usr/local/bin/gvisor-bin/gvisor_sentry ]]; then
  command -v bzip2 >/dev/null 2>&1 || { apt-get update -qq; apt-get install -y -qq bzip2; }
  base="https://storage.googleapis.com/gvisor/releases/release/${GVISOR_VERSION}/x86_64"
  cd /tmp
  rm -rf gvisor-extrait gvisor.tar.bz2 gvisor.tar.bz2.sha512 && mkdir -p gvisor-extrait
  curl -fsSL -o gvisor.tar.bz2 "${base}/gvisor.tar.bz2"
  curl -fsSL -o gvisor.tar.bz2.sha512 "${base}/gvisor.tar.bz2.sha512"
  sha512sum -c gvisor.tar.bz2.sha512
  tar xjf gvisor.tar.bz2 -C gvisor-extrait
  install -m 0755 gvisor-extrait/runsc /usr/local/bin/runsc
  install -m 0755 gvisor-extrait/containerd-shim-runsc-v1 /usr/local/bin/containerd-shim-runsc-v1
  if [[ -d gvisor-extrait/gvisor-bin ]]; then
    install -d -m 0755 /usr/local/bin/gvisor-bin
    install -m 0755 gvisor-extrait/gvisor-bin/* /usr/local/bin/gvisor-bin/
  else
    echo "L archive gVisor ne porte pas de gvisor-bin/ : structure inattendue." >&2
    tar tjf gvisor.tar.bz2 >&2
    exit 1
  fi
  rm -rf gvisor.tar.bz2 gvisor.tar.bz2.sha512 gvisor-extrait
  cd /
fi
runsc --version
[[ -x /usr/local/bin/gvisor-bin/gvisor_sentry ]]

# Le bloc .options aligne runsc sur les cgroups systemd du socle, comme runc.
if ! grep -q "runtimes.runsc" "$CONF"; then
  cat >> "$CONF" <<'TOML'

[plugins."io.containerd.cri.v1.runtime".containerd.runtimes.runsc]
  runtime_type = "io.containerd.runsc.v1"
  [plugins."io.containerd.cri.v1.runtime".containerd.runtimes.runsc.options]
    SystemdCgroup = true
TOML
  systemctl restart containerd
  sleep 10
fi
systemctl is-active containerd
attendre_l_api
# grep -c lit toute la sortie : un grep -q qui sort au premier résultat
# tuerait crictl d'un SIGPIPE, que pipefail changerait en échec.
crictl info 2>/dev/null | grep -c runsc >/dev/null

# ---------------------------------------------------------------------------
# 2. Falco, depuis le dépôt officiel, pilote modern_ebpf : rien à compiler,
#    le noyau 6.8 d'Ubuntu 24.04 porte le BTF qu'il exige.
#
#    Trois variables pilotent le script post-installation du paquet, lues dans
#    ce script même (paquet 0.45.2) : FALCO_FRONTEND=noninteractive évite la
#    boîte de dialogue, FALCO_DRIVER_CHOICE=modern_ebpf active
#    falco-modern-bpf.service, FALCOCTL_ENABLED=no MASQUE le service qui met à
#    jour les règles tout seul. Sans ce dernier, falcoctl réécrirait
#    falco_rules.yaml dans le dos du correcteur, et « les règles fournies sont
#    intactes » ne voudrait plus rien dire.
# ---------------------------------------------------------------------------
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
# touchées : le paquet en garde l'empreinte, et falco_rules.yaml n'est pas un
# fichier de configuration du paquet, une réinstallation le rétablit donc.
attendu=$(awk '$2 == "etc/falco/falco_rules.yaml" {print $1}' /var/lib/dpkg/info/falco.md5sums)
if [[ -z "$attendu" ]] || [[ "$(md5sum /etc/falco/falco_rules.yaml 2>/dev/null | cut -d' ' -f1)" != "$attendu" ]]; then
  installer_falco --reinstall
fi

# Aucune règle personnalisée : le fichier local revient à son contenu livré,
# et rules.d est vidé.
printf '%s\n' '# Your custom rules!' > /etc/falco/falco_rules.local.yaml
rm -rf /etc/falco/rules.d
install -d -m 0755 /etc/falco/rules.d

# La sortie que le correcteur lit : du JSON, une alerte par ligne, dans un
# fichier. La sortie standard du service part dans /dev/null (StandardOutput=null
# dans l'unité livrée), le journal systemd ne la verrait donc pas.
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

# ---------------------------------------------------------------------------
# 3. Istio en profil minimal (istiod seul, environ 194 Mo mesurés pour
#    cks-istio-mtls-lockdown), sans aucune exigence de chiffrement.
# ---------------------------------------------------------------------------
if ! kubectl -n istio-system get deployment istiod >/dev/null 2>&1; then
  istioctl install --set profile=minimal -y
fi
kubectl -n istio-system rollout status deployment/istiod --timeout=300s

# ---------------------------------------------------------------------------
# 4. Ce que l'apprenant doit produire est retiré s'il traîne d'un passage
#    précédent : sans cela, le challenge rendrait des points avant le travail.
# ---------------------------------------------------------------------------
kubectl delete runtimeclass "$RUNTIME_CLASS" --ignore-not-found --wait=true
kubectl -n maille delete peerauthentication --all --ignore-not-found --wait=true 2>/dev/null || true
kubectl -n donnees delete networkpolicy --all --ignore-not-found --wait=true 2>/dev/null || true
kubectl -n coffre delete pod lecteur calcul isole --ignore-not-found --wait=true 2>/dev/null || true

# Le profil AppArmor est retiré du noyau par son NOM, et tout fichier qui le
# déclare est effacé, quel que soit le nom que l'apprenant lui avait donné.
if [[ -e /sys/kernel/security/apparmor/.remove ]]; then
  printf '%s' "$PROFIL_APPARMOR" > /sys/kernel/security/apparmor/.remove 2>/dev/null || true
fi
{ grep -lsE "^[[:space:]]*profile[[:space:]]+${PROFIL_APPARMOR}([[:space:]]|\{|$)" /etc/apparmor.d/* || true; } \
  | xargs -r rm -f

# Le répertoire des profils seccomp locaux est créé VIDE : le kubelet ne le
# crée pas, et l'apprenant qui dépose son profil au bon endroit recevrait sinon
# une erreur de montage qui n'est pas la sienne.
mkdir -p "$(dirname "$PROFIL_SECCOMP")"
rm -f "$PROFIL_SECCOMP"

# ---------------------------------------------------------------------------
# 5. Les quatre namespaces et les Pods fournis.
# ---------------------------------------------------------------------------
for ns in coffre maille exterieur donnees; do
  attendre_namespace_libre "$ns"
  kubectl get namespace "$ns" >/dev/null 2>&1 || kubectl create namespace "$ns"
done
kubectl label namespace maille istio-injection=enabled --overwrite
kubectl label namespace exterieur istio-injection- 2>/dev/null || true

kubectl -n coffre delete pod tresor ordinaire --ignore-not-found --wait=true
kubectl -n maille delete pod api client-maille --ignore-not-found --wait=true
kubectl -n exterieur delete pod client-nu curieux vitrine --ignore-not-found --wait=true
kubectl -n donnees delete pod base appli intrus annuaire --ignore-not-found --wait=true

kubectl apply -f - <<YAML
# coffre : le Pod protégé, que Falco doit surveiller, et le témoin du runtime
# par défaut. Tous deux sur k8s-cp.lab, le seul nœud où Falco et runsc vivent.
apiVersion: v1
kind: Pod
metadata:
  name: tresor
  namespace: coffre
  labels:
    app: tresor
spec:
  nodeName: ${NOEUD}
  containers:
    - name: tresor
      image: ${BUSYBOX}
      command: ["sh", "-c", "sleep 86400"]
---
apiVersion: v1
kind: Pod
metadata:
  name: ordinaire
  namespace: coffre
  labels:
    app: ordinaire
spec:
  nodeName: ${NOEUD}
  containers:
    - name: outil
      image: ${BUSYBOX}
      command: ["sh", "-c", "sleep 86400"]
---
# maille : le service appelé et son client, tous deux avec un sidecar.
apiVersion: v1
kind: Pod
metadata:
  name: api
  namespace: maille
  labels:
    app: api
spec:
  containers:
    - name: web
      image: ${NGINX}
      ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: maille
spec:
  selector:
    app: api
  ports:
    - port: 80
      targetPort: 80
---
apiVersion: v1
kind: Pod
metadata:
  name: client-maille
  namespace: maille
  labels:
    app: client
spec:
  containers:
    - name: outil
      image: ${BUSYBOX}
      command: ["sh", "-c", "sleep 86400"]
---
# exterieur : hors du maillage et hors du namespace fermé.
apiVersion: v1
kind: Pod
metadata:
  name: client-nu
  namespace: exterieur
spec:
  containers:
    - name: outil
      image: ${BUSYBOX}
      command: ["sh", "-c", "sleep 86400"]
---
# curieux est sur k8s-cp.lab À DESSEIN : un shell ouvert sur un nœud que Falco
# ne regarde pas ne déclencherait rien, et le contrôle « pas ailleurs » serait
# vrai même pour une règle qui alerte sur tous les namespaces.
apiVersion: v1
kind: Pod
metadata:
  name: curieux
  namespace: exterieur
spec:
  nodeName: ${NOEUD}
  containers:
    - name: outil
      image: ${BUSYBOX}
      command: ["sh", "-c", "sleep 86400"]
---
# vitrine écoute VRAIMENT, hors de donnees et sans politique : c'est elle qui
# distingue « la sortie de donnees est fermée » de « personne n'écoutait ».
apiVersion: v1
kind: Pod
metadata:
  name: vitrine
  namespace: exterieur
  labels:
    app: vitrine
spec:
  containers:
    - name: web
      image: ${NGINX}
      ports:
        - containerPort: 80
---
# donnees : la base, son client légitime, un intrus et un second serveur.
apiVersion: v1
kind: Pod
metadata:
  name: base
  namespace: donnees
  labels:
    app: base
spec:
  containers:
    - name: base
      image: ${NGINX}
      ports:
        - containerPort: 80
---
apiVersion: v1
kind: Pod
metadata:
  name: appli
  namespace: donnees
  labels:
    app: appli
spec:
  containers:
    - name: client
      image: ${BUSYBOX}
      command: ["sh", "-c", "sleep 86400"]
---
apiVersion: v1
kind: Pod
metadata:
  name: intrus
  namespace: donnees
  labels:
    tier: inconnu
spec:
  containers:
    - name: client
      image: ${BUSYBOX}
      command: ["sh", "-c", "sleep 86400"]
---
apiVersion: v1
kind: Pod
metadata:
  name: annuaire
  namespace: donnees
  labels:
    app: annuaire
spec:
  containers:
    - name: service
      image: ${NGINX}
      ports:
        - containerPort: 80
YAML

kubectl -n coffre wait --for=condition=ready pod/tresor pod/ordinaire --timeout=240s
kubectl -n maille wait --for=condition=ready pod/api pod/client-maille --timeout=300s
kubectl -n exterieur wait --for=condition=ready pod/client-nu pod/curieux pod/vitrine --timeout=240s
kubectl -n donnees wait --for=condition=ready pod/base pod/appli pod/intrus pod/annuaire --timeout=240s

# ---------------------------------------------------------------------------
# 6. LE SETUP ÉCHOUE CHEZ LUI, PAS LE CHALLENGE AILLEURS.
#
#    Deux sondes, chacune retirée derrière elle.
#
#    a. Un Pod démarre-t-il vraiment dans runsc ? containerd peut déclarer le
#       runtime et aucun Pod n'y démarrer (relevé de cks-runtime-sandbox-gvisor
#       du 2026-10-12). Namespace jetable, rendu par le trap.
#    b. Falco voit-il le NAMESPACE Kubernetes d'un shell ? La règle demandée
#       repose sur ce champ, fourni par le greffon container à partir des
#       étiquettes du runtime. S'il manquait, aucune règle de l'apprenant ne
#       pourrait réussir, et il chercherait la faute dans la sienne.
# ---------------------------------------------------------------------------
NS_SONDE=dsoxlab-sonde-runsc
SONDE_FALCO=/etc/falco/rules.d/zz-dsoxlab-sonde.yaml
retirer_les_sondes() {
  kubectl delete namespace "$NS_SONDE" --ignore-not-found --wait=false >/dev/null 2>&1 || true
  kubectl delete runtimeclass sonde-runsc --ignore-not-found --wait=false >/dev/null 2>&1 || true
  if [[ -f "$SONDE_FALCO" ]]; then
    rm -f "$SONDE_FALCO"
    systemctl restart falco-modern-bpf.service || true
  fi
}
trap retirer_les_sondes EXIT

attendre_namespace_libre "$NS_SONDE"
kubectl delete runtimeclass sonde-runsc --ignore-not-found --wait=true
kubectl create namespace "$NS_SONDE" >/dev/null
kubectl apply -f - <<YAML
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: sonde-runsc
handler: runsc
---
apiVersion: v1
kind: Pod
metadata:
  name: sonde-runsc
  namespace: ${NS_SONDE}
spec:
  runtimeClassName: sonde-runsc
  nodeName: ${NOEUD}
  restartPolicy: Never
  containers:
    - name: sonde
      image: ${BUSYBOX}
      command: ["sh", "-c", "sleep 300"]
YAML
if ! kubectl -n "$NS_SONDE" wait --for=condition=ready pod/sonde-runsc --timeout=180s; then
  echo "AUCUN Pod ne demarre dans runsc :" >&2
  kubectl -n "$NS_SONDE" describe pod sonde-runsc >&2 || true
  journalctl -u containerd -n 60 --no-pager >&2 || true
  exit 1
fi
kubectl -n "$NS_SONDE" delete pod sonde-runsc --ignore-not-found --wait=true
kubectl delete runtimeclass sonde-runsc --ignore-not-found --wait=true
kubectl delete namespace "$NS_SONDE" --ignore-not-found --wait=true

cat > "$SONDE_FALCO" <<'YAML'
- rule: dsoxlab-sonde
  desc: Sonde du setup, retiree aussitot
  condition: spawned_process and container and k8s.ns.name = "exterieur" and proc.cmdline contains "dsoxlab-sonde-falco"
  output: "sonde dsoxlab ns=%k8s.ns.name pod=%k8s.pod.name"
  priority: NOTICE
YAML
systemctl restart falco-modern-bpf.service
attendre_falco
sleep 5
vue=0
for _ in $(seq 1 10); do
  kubectl -n exterieur exec curieux -- sh -c 'echo dsoxlab-sonde-falco' >/dev/null
  sleep 3
  if grep -qE '"rule": ?"dsoxlab-sonde"' "$FALCO_JOURNAL"; then
    vue=1
    break
  fi
done
if [[ "$vue" != 1 ]]; then
  echo "Falco ne voit pas le namespace d'un shell ouvert dans un Pod. Fin du journal :" >&2
  tail -n 20 "$FALCO_JOURNAL" >&2 || true
  journalctl -u falco-modern-bpf.service -n 60 --no-pager >&2 || true
  exit 1
fi
rm -f "$SONDE_FALCO"
systemctl restart falco-modern-bpf.service
attendre_falco
trap - EXIT

echo "Challenge posé : rien n'est confiné, le maillage est permissif, donnees est ouvert, Falco ne surveille pas le coffre."
