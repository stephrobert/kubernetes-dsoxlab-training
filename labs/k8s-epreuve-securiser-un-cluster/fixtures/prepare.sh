#!/usr/bin/env bash
# Pose l'état hérité de l'épreuve k8s-epreuve-securiser-un-cluster, faux sur les
# dix-neuf états par construction :
#
#   - plan de contrôle : les manifestes de kubeadm tels qu'installés, profileur
#     ouvert sur les trois composants, aucun audit ;
#   - boutique : le catalogue (nginx-unprivileged 1.21, par TAG, 2 réplicas,
#     sans contexte de sécurité), son Service, son Secret, et outil-ancien, un
#     Pod privilégié ; aucun standard, aucune politique d'admission ;
#   - facturation : export-comptable (le Pod surveillé) et temoin-noyau (témoin
#     du runtime par défaut), sur k8s-cp.lab, là où vivent Falco, runsc et les
#     profils ;
#   - commandes : un maillage Istio permissif (suivi, panier) ;
#   - partenaires : transporteur (sans sidecar), visiteur (l'outil réseau
#     d'ailleurs, sur k8s-cp.lab) et site-partenaire (une cible hors de
#     paiement) ;
#   - paiement : grand-livre, caisse, publicite et fidelite, sans politique
#     réseau ;
#   - registre : un registre local sur le port 5000 du nœud, qui porte l'image
#     d'origine du catalogue et une autre image, aucune signée ;
#   - nœud : Falco (modern_ebpf, sortie JSON), gVisor connu de containerd,
#     trivy, cosign, crane et istioctl, le Dockerfile du catalogue en
#     /root/boutique, et l'audit CIS de départ mesuré.
#
# Chaque brique reprend un lab attesté : cks-api-server-hardening,
# cks-cis-benchmark-remediate, cks-audit-log-policy, cks-pod-security-admission,
# cks-validating-admission-policy, cks-secure-existing-pod,
# cks-apparmor-confiner-un-pod, cks-seccomp-profile, cks-runtime-sandbox-gvisor,
# cks-istio-mtls-lockdown, cks-networkpolicy-default-deny,
# cks-image-pinned-digest, cks-cosign-verify-image, cks-image-scanning-trivy,
# cks-dockerfile-static-analysis ; l'installation de Falco reprend
# k8s-challenge-confiner-et-detecter, avec d'autres espaces, d'autres Pods et
# une autre règle à écrire que ce challenge (décision D57).
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
IMAGE_ORIGINE=nginxinc/nginx-unprivileged:1.21
ETAT=/var/lib/dsoxlab/epreuve-securiser-un-cluster
MANIFESTES=/etc/kubernetes/manifests
COMPOSANTS=(kube-apiserver kube-controller-manager kube-scheduler)
NAMESPACES=(boutique facturation commandes partenaires paiement registre conformite)

# gVisor épinglé sur une publication datée (relevé du 2026-11-14 dans le dépôt
# officiel storage.googleapis.com/gvisor), Falco sur la dernière version de
# l'index du dépôt officiel falcosecurity à la même date.
GVISOR_VERSION=20261026.0
FALCO_VERSION=0.45.2
FALCO_JOURNAL=/var/log/falco/events.json

mkdir -p "$ETAT" /var/backups

attendre_le_control_plane() {
  for _ in $(seq 1 60); do
    kubectl get --raw /healthz >/dev/null 2>&1 && break
    sleep 3
  done
  kubectl get --raw /healthz >/dev/null
  # /healthz répond avant que les Pods statiques ne soient revenus Running.
  for _ in $(seq 1 40); do
    phases=$(kubectl -n kube-system get pods -l tier=control-plane \
      -o jsonpath='{.items[*].status.phase}' 2>/dev/null || true)
    [[ -n "$phases" && "$phases" != *Pending* ]] && return 0
    sleep 3
  done
  echo "Le control plane ne revient pas en Running." >&2
  return 1
}

attendre_namespace_libre() {
  if [[ "$(kubectl get namespace "$1" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
    kubectl wait --for=delete "namespace/$1" --timeout=240s
  fi
}

# ---------------------------------------------------------------------------
# 1. Le plan de contrôle, tel que kubeadm l'a installé. Les sauvegardes vivent
#    dans /var/backups, JAMAIS dans /etc/kubernetes/manifests, que le kubelet
#    lancerait comme seconds Pods statiques (cks-api-server-hardening).
# ---------------------------------------------------------------------------
restaure=0
for composant in "${COMPOSANTS[@]}"; do
  sauvegarde="/var/backups/${composant}.avant-epreuve-n5.yaml"
  if [[ -f "$sauvegarde" ]]; then
    if ! cmp -s "$sauvegarde" "${MANIFESTES}/${composant}.yaml"; then
      cp -f "$sauvegarde" "${MANIFESTES}/${composant}.yaml"
      restaure=1
    fi
  else
    cp -f "${MANIFESTES}/${composant}.yaml" "$sauvegarde"
  fi
done
[[ "$restaure" == 1 ]] && sleep 20
attendre_le_control_plane
if grep -q -- "--profiling=false" "${MANIFESTES}/kube-apiserver.yaml" \
   || grep -q -- "--audit-policy-file" "${MANIFESTES}/kube-apiserver.yaml"; then
  echo "Le manifeste de l'API server est deja durci : la restauration n'a pas marche." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# 2. gVisor : il redémarre containerd, donc AVANT tout Pod de l'épreuve.
# ---------------------------------------------------------------------------
CONF=/etc/containerd/config.toml
[[ -f /var/backups/containerd.avant-gvisor.toml ]] || cp -f "$CONF" /var/backups/containerd.avant-gvisor.toml
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
    exit 1
  fi
  rm -rf gvisor.tar.bz2 gvisor.tar.bz2.sha512 gvisor-extrait
  cd /
fi
runsc --version
[[ -x /usr/local/bin/gvisor-bin/gvisor_sentry ]]
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
attendre_le_control_plane
crictl info 2>/dev/null | grep -c runsc >/dev/null

# ---------------------------------------------------------------------------
# 3. Falco, comme k8s-challenge-confiner-et-detecter : dépôt officiel, paquet
#    épinglé, modern_ebpf, falcoctl masqué, règles fournies remises d'origine,
#    aucune règle personnalisée, sortie JSON dans un fichier.
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
attendu=$(awk '$2 == "etc/falco/falco_rules.yaml" {print $1}' /var/lib/dpkg/info/falco.md5sums)
if [[ -z "$attendu" ]] || [[ "$(md5sum /etc/falco/falco_rules.yaml 2>/dev/null | cut -d' ' -f1)" != "$attendu" ]]; then
  installer_falco --reinstall
fi
printf '%s\n' '# Your custom rules!' > /etc/falco/falco_rules.local.yaml
rm -rf /etc/falco/rules.d
install -d -m 0755 /etc/falco/rules.d
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
  echo "Falco ne repond pas :" >&2
  journalctl -u falco-modern-bpf.service -n 60 --no-pager >&2 || true
  return 1
}
systemctl enable falco-modern-bpf.service
systemctl restart falco-modern-bpf.service
attendre_falco

# ---------------------------------------------------------------------------
# 4. Istio, profil minimal, sans exigence. Une exigence de tout le maillage
#    laissée dans istio-system par un passage précédent est retirée.
# ---------------------------------------------------------------------------
if ! kubectl -n istio-system get deployment istiod >/dev/null 2>&1; then
  istioctl install --set profile=minimal -y
fi
kubectl -n istio-system rollout status deployment/istiod --timeout=300s
kubectl -n istio-system delete peerauthentication --all --ignore-not-found --wait=true 2>/dev/null || true

# ---------------------------------------------------------------------------
# 5. Les objets de CLUSTER que l'apprenant créera (classes de runtime,
#    politiques d'admission et leurs liaisons) n'ont pas de nom imposé. On
#    relève donc ceux qui existent AVANT l'épreuve, une seule fois, et tout ce
#    qui n'est pas dans ce relevé est retiré ici comme au nettoyage.
# ---------------------------------------------------------------------------
noms() { kubectl get "$1" -o name 2>/dev/null | sort; }
for type in runtimeclasses validatingadmissionpolicybindings validatingadmissionpolicies; do
  [[ -f "${ETAT}/${type}.avant" ]] || noms "$type" > "${ETAT}/${type}.avant"
done
for type in validatingadmissionpolicybindings validatingadmissionpolicies runtimeclasses; do
  comm -13 "${ETAT}/${type}.avant" <(noms "$type") | xargs -r kubectl delete --ignore-not-found --wait=true
done

# Les profils que les Pods d'un passage précédent déclaraient : le nom du
# profil AppArmor et le chemin du profil seccomp sont libres, on les lit donc
# sur les Pods avant de les retirer.
profil_aa=$(kubectl -n facturation get pod consultation -o json 2>/dev/null \
  | python3 -c 'import json,sys
p=json.load(sys.stdin)["spec"]
c=[p.get("securityContext") or {}]+[x.get("securityContext") or {} for x in p["containers"]]
print(" ".join(sorted({(s.get("appArmorProfile") or {}).get("localhostProfile","") for s in c} - {""})))' 2>/dev/null || true)
for nom in $profil_aa; do
  printf '%s' "$nom" > /sys/kernel/security/apparmor/.remove 2>/dev/null || true
  { grep -lsE "^[[:space:]]*profile[[:space:]]+${nom}([[:space:]]|\{|$)" /etc/apparmor.d/* || true; } | xargs -r rm -f
done
profil_sc=$(kubectl -n facturation get pod numerotation -o json 2>/dev/null \
  | python3 -c 'import json,sys
p=json.load(sys.stdin)["spec"]
c=[p.get("securityContext") or {}]+[x.get("securityContext") or {} for x in p["containers"]]
print(" ".join(sorted({(s.get("seccompProfile") or {}).get("localhostProfile","") for s in c} - {""})))' 2>/dev/null || true)
for chemin in $profil_sc; do
  [[ "$chemin" == *..* ]] || rm -f "/var/lib/kubelet/seccomp/${chemin}"
done
mkdir -p /var/lib/kubelet/seccomp/profiles

# ---------------------------------------------------------------------------
# 6. Les espaces de l'épreuve, repartis de zéro : un espace recréé ne garde ni
#    label de standard, ni politique, ni clé publiée, ni Pod d'un passage
#    précédent.
# ---------------------------------------------------------------------------
kubectl delete namespace "${NAMESPACES[@]}" --ignore-not-found --wait=true --timeout=300s
for ns in "${NAMESPACES[@]}"; do
  attendre_namespace_libre "$ns"
  kubectl create namespace "$ns"
done
kubectl label namespace commandes istio-injection=enabled --overwrite

kubectl apply -f - <<YAML
# --- boutique : le catalogue, par TAG, sans contexte de sécurité -------------
apiVersion: v1
kind: Secret
metadata:
  name: catalogue-db
  namespace: boutique
stringData:
  password: s3cr3t-boutique
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: catalogue
  namespace: boutique
  labels:
    app: catalogue
spec:
  replicas: 2
  selector:
    matchLabels:
      app: catalogue
  template:
    metadata:
      labels:
        app: catalogue
    spec:
      containers:
        - name: catalogue
          image: ${IMAGE_ORIGINE}
          ports:
            - containerPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: catalogue-svc
  namespace: boutique
spec:
  selector:
    app: catalogue
  ports:
    - port: 80
      targetPort: 8080
---
# outil-ancien cumule les défauts de cks-secure-existing-pod : namespace de
# processus de l'hôte, tag flottant, conteneur privilégié, root, escalade.
apiVersion: v1
kind: Pod
metadata:
  name: outil-ancien
  namespace: boutique
  labels:
    app: outil
spec:
  hostPID: true
  containers:
    - name: outil
      image: busybox:latest
      command: ["sh", "-c", "sleep 86400"]
      securityContext:
        privileged: true
        runAsUser: 0
        allowPrivilegeEscalation: true
---
# --- facturation : les factures de la boutique --------------------------------
# export-comptable envoie chaque nuit les écritures au cabinet comptable par un
# canal déjà ouvert : aucun outil de téléchargement n'a à y tourner.
apiVersion: v1
kind: Pod
metadata:
  name: export-comptable
  namespace: facturation
  labels:
    app: export-comptable
spec:
  nodeName: ${NOEUD}
  containers:
    - name: export
      image: ${BUSYBOX}
      command: ["sh", "-c", "sleep 86400"]
---
apiVersion: v1
kind: Pod
metadata:
  name: temoin-noyau
  namespace: facturation
  labels:
    app: temoin-noyau
spec:
  nodeName: ${NOEUD}
  containers:
    - name: outil
      image: ${BUSYBOX}
      command: ["sh", "-c", "sleep 86400"]
---
# --- commandes : le suivi des commandes, dans le maillage --------------------
apiVersion: v1
kind: Pod
metadata:
  name: suivi
  namespace: commandes
  labels:
    app: suivi
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
  name: suivi
  namespace: commandes
spec:
  selector:
    app: suivi
  ports:
    - port: 80
      targetPort: 80
---
apiVersion: v1
kind: Pod
metadata:
  name: panier
  namespace: commandes
  labels:
    app: panier
spec:
  containers:
    - name: outil
      image: ${BUSYBOX}
      command: ["sh", "-c", "sleep 86400"]
---
# --- partenaires : hors du maillage et hors de paiement ----------------------
apiVersion: v1
kind: Pod
metadata:
  name: transporteur
  namespace: partenaires
  labels:
    app: transporteur
spec:
  containers:
    - name: outil
      image: ${BUSYBOX}
      command: ["sh", "-c", "sleep 86400"]
---
# Sur k8s-cp.lab, là où Falco regarde : un outil réseau lancé ailleurs doit
# être VU pour que son silence prouve quelque chose.
apiVersion: v1
kind: Pod
metadata:
  name: visiteur
  namespace: partenaires
  labels:
    app: visiteur
spec:
  nodeName: ${NOEUD}
  containers:
    - name: outil
      image: ${BUSYBOX}
      command: ["sh", "-c", "sleep 86400"]
---
apiVersion: v1
kind: Pod
metadata:
  name: site-partenaire
  namespace: partenaires
  labels:
    app: site-partenaire
spec:
  containers:
    - name: web
      image: ${NGINX}
      ports:
        - containerPort: 80
---
# --- paiement : le grand livre, la caisse qui l'alimente, un traceur
# publicitaire embarqué par erreur, et le programme de fidélité ----------------
apiVersion: v1
kind: Pod
metadata:
  name: grand-livre
  namespace: paiement
  labels:
    app: grand-livre
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
  name: caisse
  namespace: paiement
  labels:
    app: caisse
spec:
  containers:
    - name: client
      image: ${BUSYBOX}
      command: ["sh", "-c", "sleep 86400"]
---
apiVersion: v1
kind: Pod
metadata:
  name: publicite
  namespace: paiement
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
  name: fidelite
  namespace: paiement
  labels:
    app: fidelite
spec:
  containers:
    - name: service
      image: ${NGINX}
      ports:
        - containerPort: 80
---
# --- registre : local, en hostNetwork sur le port 5000 de k8s-cp.lab, comme
# cks-cosign-verify-image. Signer POUSSE la signature à côté de l'image : aucun
# registre public ne l'accepterait sans identifiants.
apiVersion: v1
kind: Pod
metadata:
  name: registre
  namespace: registre
  labels:
    app: registre
spec:
  nodeName: ${NOEUD}
  hostNetwork: true
  containers:
    - name: registry
      image: registry:2
      ports:
        - containerPort: 5000
          hostPort: 5000
YAML

kubectl -n boutique rollout status deployment/catalogue --timeout=300s
kubectl -n boutique wait --for=condition=ready pod/outil-ancien --timeout=240s
kubectl -n facturation wait --for=condition=ready pod/export-comptable pod/temoin-noyau --timeout=240s
kubectl -n commandes wait --for=condition=ready pod/suivi pod/panier --timeout=300s
kubectl -n partenaires wait --for=condition=ready pod/transporteur pod/visiteur pod/site-partenaire --timeout=240s
kubectl -n paiement wait --for=condition=ready pod/grand-livre pod/caisse pod/publicite pod/fidelite --timeout=240s
kubectl -n registre wait --for=condition=ready pod/registre --timeout=240s

# ---------------------------------------------------------------------------
# 7. Le registre : on attend qu'il RÉPONDE, puis il reçoit l'image d'origine du
#    catalogue et une autre image, aucune signée.
# ---------------------------------------------------------------------------
for _ in $(seq 1 30); do
  curl -sf http://localhost:5000/v2/ >/dev/null 2>&1 && break
  sleep 2
done
curl -sf http://localhost:5000/v2/ >/dev/null
crane copy "$IMAGE_ORIGINE" localhost:5000/boutique/catalogue:1.21
crane copy "$BUSYBOX" localhost:5000/boutique/outil:1.0
crane ls localhost:5000/boutique/catalogue
crane ls localhost:5000/boutique/outil

# ---------------------------------------------------------------------------
# 8. L'audit CIS de départ, MESURÉ et non écrit en dur : le test le compare à
#    l'audit qu'il rejoue. Le Job est celui de cks-cis-benchmark-remediate.
# ---------------------------------------------------------------------------
crictl pull aquasec/kube-bench:v0.16.0@sha256:75506f222d1eb6ce2a751a5533bdc0a3b54c898e2e49e7751d0ee22cfb862679 >/dev/null 2>&1 || true
kubectl apply -f - <<'YAML'
apiVersion: batch/v1
kind: Job
metadata:
  name: kube-bench-depart
  namespace: conformite
spec:
  backoffLimit: 1
  template:
    spec:
      nodeName: k8s-cp.lab
      hostPID: true
      restartPolicy: Never
      containers:
        - name: kube-bench
          image: aquasec/kube-bench:v0.16.0@sha256:75506f222d1eb6ce2a751a5533bdc0a3b54c898e2e49e7751d0ee22cfb862679
          command: ["kube-bench", "run", "--targets", "master", "--json"]
          volumeMounts:
            - name: var-lib-etcd
              mountPath: /var/lib/etcd
              readOnly: true
            - name: var-lib-kubelet
              mountPath: /var/lib/kubelet
              readOnly: true
            - name: etc-kubernetes
              mountPath: /etc/kubernetes
              readOnly: true
            - name: usr-bin
              mountPath: /usr/local/mount-from-host/bin
              readOnly: true
      volumes:
        - name: var-lib-etcd
          hostPath: {path: /var/lib/etcd}
        - name: var-lib-kubelet
          hostPath: {path: /var/lib/kubelet}
        - name: etc-kubernetes
          hostPath: {path: /etc/kubernetes}
        - name: usr-bin
          hostPath: {path: /usr/bin}
YAML
kubectl -n conformite wait --for=condition=complete job/kube-bench-depart --timeout=300s
kubectl -n conformite logs job/kube-bench-depart > "${ETAT}/kube-bench-depart.log"
python3 - "${ETAT}/kube-bench-depart.log" "${ETAT}/echecs-cis-depart" <<'PY'
import json, sys
texte = open(sys.argv[1], encoding="utf-8").read()
rapport = json.loads(texte[texte.index("{"):])
total = sum(int(c.get("total_fail", 0)) for c in rapport.get("Controls", []))
etats = {str(r.get("test_number")): r.get("status")
         for c in rapport.get("Controls", []) for g in c.get("tests", []) for r in g.get("results", [])}
for numero in ("1.2.15", "1.3.2", "1.4.1"):
    if etats.get(numero) != "FAIL":
        sys.exit(f"Le controle {numero} ne part pas en echec ({etats.get(numero)}) : l'epreuve ne mesurerait rien.")
open(sys.argv[2], "w", encoding="utf-8").write(f"{total}\n")
print(f"Audit CIS de depart : {total} echecs.")
PY
kubectl -n conformite delete job kube-bench-depart --ignore-not-found --wait=true

# ---------------------------------------------------------------------------
# 9. trivy : base téléchargée et image d'origine déjà analysée, pour que ni le
#    premier scan de l'apprenant ni celui du correcteur ne la tirent.
# ---------------------------------------------------------------------------
trivy image --quiet --download-db-only 2>&1 | tail -3 || true
trivy image --quiet --scanners vuln --severity CRITICAL "$IMAGE_ORIGINE" >/dev/null 2>&1 || true

# ---------------------------------------------------------------------------
# 10. Les sondes : un Pod démarre-t-il dans runsc, et Falco voit-il wget
#     lancé dans un Pod, avec son namespace ? Chacune est retirée derrière elle.
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
  condition: spawned_process and container and k8s.ns.name = "partenaires" and proc.name = "wget" and proc.cmdline contains "dsoxlab-sonde-falco"
  output: "sonde dsoxlab ns=%k8s.ns.name pod=%k8s.pod.name proc=%proc.name"
  priority: NOTICE
YAML
systemctl restart falco-modern-bpf.service
attendre_falco
sleep 5
vue=0
# La sonde lance wget comme le correcteur, directement par l'exec et sans
# shell : elle prouve que Falco voit le namespace ET nomme le processus wget,
# les deux faits sur lesquels la règle de l'épreuve repose.
for _ in $(seq 1 10); do
  kubectl -n partenaires exec visiteur -- wget -q -T 1 -O /dev/null http://127.0.0.1:9/dsoxlab-sonde-falco >/dev/null 2>&1 || true
  sleep 3
  if grep -qE '"rule": ?"dsoxlab-sonde"' "$FALCO_JOURNAL"; then
    vue=1
    break
  fi
done
if [[ "$vue" != 1 ]]; then
  echo "Falco ne voit pas wget lance dans un Pod de partenaires :" >&2
  tail -n 20 "$FALCO_JOURNAL" >&2 || true
  journalctl -u falco-modern-bpf.service -n 60 --no-pager >&2 || true
  exit 1
fi
rm -f "$SONDE_FALCO"
systemctl restart falco-modern-bpf.service
attendre_falco
trap - EXIT

# Le profileur doit être OUVERT au départ, sinon P01 ne mesure rien.
kubectl get --raw /debug/pprof/ >/dev/null

echo "Etat herite pose : rien n'est durci, confine, exige, ferme, surveille ni signe."
