#!/usr/bin/env bash
# Pose la situation : un noeud dont containerd connait DEUX runtimes, et un
# namespace vide.
#
# Le runtime est installe par le setup, pas par le candidat : installer gVisor
# n'est pas la competence que l'examen mesure, et cela prendrait la moitie du
# temps du lab. Ce qui est demande au candidat, c'est de s'en servir.
#
# TROIS PIEGES DE DISTRIBUTION, mesures le 2026-09-16 :
#
#   1. gVisor ne publie plus ses binaires separement. L'URL
#      .../latest/x86_64/containerd-shim-runsc-v1 rend 404, et seule l'archive
#      gvisor.tar.bz2 porte encore le shim.
#   2. bzip2 n'est pas installe sur une Ubuntu 24.04 minimale : tar echoue avec
#      « bzip2: Cannot exec ».
#   3. Le paquet APT `runsc` d'Ubuntu date de 2023 et ne fournit pas le shim.
#   4. L'archive ne contient plus deux binaires mais SEPT, dont un repertoire
#      `gvisor-bin/` que runsc exige : gvisor_sentry, gvisor-sentry-prewarmer,
#      checkpointgofer, runsc-fd-parking, runsc-metric-server. Mesure le
#      2026-10-14 : n'installer que runsc et le shim fait echouer tout Pod avec
#      « sidecar "gvisor_sentry" not usable (stat
#      /usr/local/bin/gvisor-bin/gvisor_sentry: no such file or directory) and
#      --sidecar-usage-policy is set to STRICT ». Le message n'apparait que dans
#      le journal de containerd, jamais dans la sortie de kubectl, qui se
#      contente d'un delai depasse sur le Pod.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

CONF=/etc/containerd/config.toml
SAUVEGARDE=/var/backups/containerd.avant-gvisor.toml
mkdir -p /var/backups

attendre_l_api() {
  for _ in $(seq 1 60); do
    kubectl get --raw /healthz >/dev/null 2>&1 && return 0
    sleep 3
  done
  echo "L API server ne repond plus apres le redemarrage de containerd." >&2
  return 1
}

if [[ ! -f "$SAUVEGARDE" ]]; then
  cp -f "$CONF" "$SAUVEGARDE"
fi

# La garde regarde AUSSI gvisor-bin/ : un noeud qui porte deja runsc d'une
# installation anterieure a ce correctif ne reinstallerait jamais le repertoire
# manquant, et le lab resterait injouable sans que rien ne le dise.
if ! command -v runsc >/dev/null 2>&1 \
   || [[ ! -x /usr/local/bin/containerd-shim-runsc-v1 ]] \
   || [[ ! -x /usr/local/bin/gvisor-bin/gvisor_sentry ]]; then
  command -v bzip2 >/dev/null 2>&1 || { apt-get update -qq; apt-get install -y -qq bzip2; }
  cd /tmp
  rm -rf gvisor-extrait && mkdir -p gvisor-extrait
  curl -fsSL -o gvisor.tar.bz2 \
    "https://storage.googleapis.com/gvisor/releases/release/latest/x86_64/gvisor.tar.bz2"
  tar xjf gvisor.tar.bz2 -C gvisor-extrait
  install -m 0755 gvisor-extrait/runsc /usr/local/bin/runsc
  install -m 0755 gvisor-extrait/containerd-shim-runsc-v1 \
    /usr/local/bin/containerd-shim-runsc-v1
  # Tout `gvisor-bin/`, et non les seuls binaires qu'on croit utiles : runsc
  # choisit lui-meme lesquels il appelle, selon la plateforme et ses options.
  if [[ -d gvisor-extrait/gvisor-bin ]]; then
    install -d -m 0755 /usr/local/bin/gvisor-bin
    install -m 0755 gvisor-extrait/gvisor-bin/* /usr/local/bin/gvisor-bin/
  else
    echo "L archive gVisor ne porte pas de gvisor-bin/ : structure inattendue." >&2
    tar tjf gvisor.tar.bz2 >&2
    exit 1
  fi
  rm -rf gvisor.tar.bz2 gvisor-extrait
fi
runsc --version | head -1
# Ce que runsc attend doit etre la AVANT qu'un Pod ne le demande : un sentry
# absent ne se voit sinon que dans le journal de containerd.
[[ -x /usr/local/bin/gvisor-bin/gvisor_sentry ]] || {
  echo "gvisor_sentry absent de /usr/local/bin/gvisor-bin/ apres installation." >&2
  ls -la /usr/local/bin/gvisor-bin/ >&2 2>/dev/null || true
  exit 1
}

# Le bloc .options n'est PAS decoratif. Le socle aligne runc sur les cgroups
# systemd (`SystemdCgroup = true`), parce que sans cela le kubelet et containerd
# gerent les cgroups differemment et le noeud reste NotReady sans message.
# Une section runsc SANS options garde le defaut de containerd, cgroupfs : le
# noeud se retrouve avec DEUX pilotes de cgroups, et un Pod en
# runtimeClassName: gvisor n'a jamais de cgroup coherent.
#
# Mesure le 2026-10-14 sur containerd 2.2.1, la version qu'Ubuntu 24.04 installe
# aujourd'hui : `containerd config dump` ne montrait `SystemdCgroup` qu'UNE
# fois, sous runc. Le chemin de plugin, lui, est bien le bon : runsc apparait
# dans la configuration effective.
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

# LE SETUP DOIT ECHOUER CHEZ LUI, PAS LAISSER LE LAB ECHOUER AILLEURS.
#
# Jusqu'ici ce script contrôlait que containerd redemarre et que l'API repond.
# Les deux passent sur un noeud ou aucun Pod gVisor ne peut demarrer, et l'echec
# surgissait trois minutes plus tard dans la solution du formateur, sous la
# forme d'un « timed out waiting for the condition on pods/confine » qui ne
# nomme pas sa cause. C'est ce qu'a vecu le relevé du 2026-10-12.
#
# Deux sondes, et la seconde est la seule qui prouve quelque chose : la premiere
# dit que containerd a LU la declaration, pas que gVisor tourne sur ce noyau.
echo "Sonde 1/2 : le runtime runsc est-il enregistre aupres du CRI ?"
if ! crictl info 2>/dev/null | grep -q runsc; then
  echo "containerd ne declare pas runsc au CRI. Configuration effective :" >&2
  containerd config dump 2>/dev/null | grep -A6 "runtimes" >&2 || true
  exit 1
fi

echo "Sonde 2/2 : un Pod peut-il reellement demarrer dans runsc ?"

# LA SONDE NE TOUCHE PAS A CE QUI APPARTIENT AU LAB.
#
# Elle emprunta d'abord `bac-a-sable`, le namespace du lab, et elle etait placee
# AVANT le bloc qui attend la fin d'une suppression en cours. Mesure le
# 2026-10-15 : « pods "sonde-runsc" is forbidden: unable to create new content
# in namespace bac-a-sable because it is being terminated ». La sonde est sortie
# en 1 avant son propre nettoyage, a laisse sa RuntimeClass derriere elle, et le
# lab suivant a rendu ROUGE pour un objet qu'il n'avait jamais cree.
#
# Namespace jetable, donc, et rendu par un trap : qu'elle reussisse, echoue ou
# soit interrompue, elle ne laisse rien. Une sonde qui salit le cluster qu'elle
# controle n'est plus une sonde.
NS_SONDE=dsoxlab-sonde-runsc

retirer_la_sonde() {
  kubectl delete namespace "$NS_SONDE" --ignore-not-found --wait=false >/dev/null 2>&1 || true
  kubectl delete runtimeclass sonde-runsc --ignore-not-found --wait=false >/dev/null 2>&1 || true
}
trap retirer_la_sonde EXIT

# Un passage precedent a pu laisser le namespace en Terminating : on l'attend
# plutot que de creer dedans, ce qui est exactement l'erreur qu'on corrige.
if [[ "$(kubectl get namespace "$NS_SONDE" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete "namespace/$NS_SONDE" --timeout=180s || true
fi
kubectl delete runtimeclass sonde-runsc --ignore-not-found --wait=true
kubectl create namespace "$NS_SONDE" >/dev/null

kubectl apply -f - <<'YAML'
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: sonde-runsc
handler: runsc
YAML
kubectl apply -f - <<YAML
apiVersion: v1
kind: Pod
metadata:
  name: sonde-runsc
  namespace: $NS_SONDE
spec:
  runtimeClassName: sonde-runsc
  nodeName: k8s-cp.lab
  restartPolicy: Never
  containers:
    - name: sonde
      image: busybox:1.37
      command: ["sh", "-c", "sleep 300"]
YAML
if ! kubectl -n "$NS_SONDE" wait --for=condition=ready pod/sonde-runsc --timeout=180s; then
  echo "AUCUN Pod ne demarre dans runsc. Ce que Kubernetes en dit :" >&2
  kubectl -n "$NS_SONDE" describe pod sonde-runsc >&2 || true
  echo "--- journal de containerd ---" >&2
  journalctl -u containerd -n 60 --no-pager >&2 || true
  exit 1   # le trap retire la sonde
fi
echo "gVisor fonctionne : la sonde a demarre."

# Retrait immediat et ATTENDU, pour que la photographie du validateur ne voie
# pas un namespace en cours de suppression. Le trap reste armé au cas où.
kubectl -n "$NS_SONDE" delete pod sonde-runsc --ignore-not-found --wait=true
kubectl delete runtimeclass sonde-runsc --ignore-not-found --wait=true
kubectl delete namespace "$NS_SONDE" --ignore-not-found --wait=true
trap - EXIT

# Ce que le candidat doit produire est retire s'il traine d'un passage
# precedent : la RuntimeClass est un objet de CLUSTER et survivrait au
# namespace.
kubectl delete runtimeclass gvisor --ignore-not-found --wait=true

if [[ "$(kubectl get namespace bac-a-sable -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/bac-a-sable --timeout=180s
fi
kubectl get namespace bac-a-sable >/dev/null 2>&1 || kubectl create namespace bac-a-sable
kubectl -n bac-a-sable delete pod confine ordinaire --ignore-not-found --wait=true

# Le Pod temoin, lance par le runtime PAR DEFAUT. Il sert de point de
# comparaison : sans lui, on ne saurait pas distinguer « le bac a sable isole »
# de « tous les Pods voient ce noyau ».
kubectl apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: ordinaire
  namespace: bac-a-sable
spec:
  nodeName: k8s-cp.lab
  containers:
    - name: outil
      image: busybox:1.37
      command: ["sh", "-c", "sleep 86400"]
YAML
kubectl -n bac-a-sable wait --for=condition=ready pod/ordinaire --timeout=180s

echo "Situation posee : containerd connait runsc, et aucune RuntimeClass ne le declare."
