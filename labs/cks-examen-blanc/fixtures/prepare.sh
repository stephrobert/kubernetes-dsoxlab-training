#!/usr/bin/env bash
# Pose l'examen blanc CKS sur le cluster kubeadm du catalogue. Joué en root sur
# k8s-cp.lab, après l'installation de Traefik et des outils (trivy, cosign,
# crane), avant la mécanique d'examen (shared/examen-ssh.yml).
#
#   - le plan de contrôle repart des manifestes d'origine, sauvegardés dans
#     /var/backups et JAMAIS dans /etc/kubernetes/manifests (le kubelet y
#     lancerait la copie comme un second Pod statique) ;
#   - chaque namespace de l'examen est supprimé puis recréé : un passage
#     précédent ne laisse ni politique, ni label, ni Secret ;
#   - ~/examen/ : le Job kube-bench et le Dockerfile à corriger ;
#   - l'état de départ de chaque tâche, faux par construction, puis des gardes
#     qui échouent ICI si le socle a changé, plutôt que de laisser un test
#     vert avant le travail.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
FIX=/var/lib/dsoxlab/cks-examen
MANIFESTES=/etc/kubernetes/manifests
BUSYBOX="busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"
BUSYBOX_137="busybox@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e"
BUSYBOX_138="busybox@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"
NGINX="nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
NGINX_SANS_ROOT="nginxinc/nginx-unprivileged:1.27.5-alpine@sha256:65e3e85dbaed8ba248841d9d58a899b6197106c23cb0ff1a132b7bfe0547e4c0"
REGISTRE="registry:2.8.3@sha256:a3d8aaa63ed8681a604f1dea0aa03f100d5895b6a58ace528858a7b332415373"
KUBE_BENCH="aquasec/kube-bench:v0.16.0@sha256:75506f222d1eb6ce2a751a5533bdc0a3b54c898e2e49e7751d0ee22cfb862679"
NAMESPACES=(zone vitrine conformite equipe-dev releves confinement durci production tresor chaine
  chaine-signature coffre catalogue atelier)

attendre_le_control_plane() {
  for _ in $(seq 1 60); do
    kubectl get --raw /healthz >/dev/null 2>&1 && break
    sleep 3
  done
  kubectl get --raw /healthz >/dev/null
  # /healthz répond avant que les Pods statiques ne soient sortis de Pending.
  for _ in $(seq 1 40); do
    phases=$(kubectl -n kube-system get pods -l tier=control-plane \
      -o jsonpath='{.items[*].status.phase}' 2>/dev/null || true)
    [[ -n "$phases" && "$phases" != *Pending* ]] && return 0
    sleep 3
  done
  echo "Le plan de contrôle ne revient pas en Running." >&2
  return 1
}

# ---------------------------------------------------------------------------
# 1. Le plan de contrôle, tel que kubeadm l'a écrit (tâches 3 et 14).
# ---------------------------------------------------------------------------
mkdir -p /var/backups
for composant in kube-apiserver kube-controller-manager kube-scheduler; do
  sauvegarde="/var/backups/${composant}.avant-cks-examen.yaml"
  if [[ -f "$sauvegarde" ]]; then
    cp -f "$sauvegarde" "${MANIFESTES}/${composant}.yaml"
  else
    cp -f "${MANIFESTES}/${composant}.yaml" "$sauvegarde"
  fi
done
attendre_le_control_plane
rm -f /var/log/kubernetes/audit.log /etc/kubernetes/audit-policy.yaml
for composant in kube-apiserver kube-controller-manager kube-scheduler; do
  if grep -q -- "--profiling=false" "${MANIFESTES}/${composant}.yaml"; then
    echo "${composant} porte déjà --profiling=false : la tâche 3 serait faite avant le travail." >&2
    exit 1
  fi
done
if grep -q -- "--audit-policy-file" "${MANIFESTES}/kube-apiserver.yaml"; then
  echo "L'API server audite déjà : la tâche 14 serait faite avant le travail." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# 2. Les fichiers du nœud qu'une tâche fait écrire, retirés d'un passage
#    précédent (tâches 7 et 13).
# ---------------------------------------------------------------------------
mkdir -p /var/lib/kubelet/seccomp/profiles
rm -f /var/lib/kubelet/seccomp/profiles/restrict-chmod.json
rm -f /root/cosign.key /root/cosign.pub

# ---------------------------------------------------------------------------
# 3. Les objets de CLUSTER d'un passage précédent (tâches 4 et 11).
# ---------------------------------------------------------------------------
kubectl delete clusterrolebinding dev-admin-binding --ignore-not-found --wait=true
kubectl get validatingadmissionpolicybinding -o name 2>/dev/null \
  | grep -vE 'safe-upgrades' | xargs -r kubectl delete --ignore-not-found || true
kubectl get validatingadmissionpolicy -o name 2>/dev/null \
  | grep -vE 'safe-upgrades' | xargs -r kubectl delete --ignore-not-found || true

# ---------------------------------------------------------------------------
# 4. Les namespaces, neufs.
# ---------------------------------------------------------------------------
kubectl delete namespace "${NAMESPACES[@]}" --ignore-not-found --wait=true --timeout=300s
for ns in "${NAMESPACES[@]}"; do
  kubectl create namespace "$ns"
done

# ---------------------------------------------------------------------------
# 5. Les fichiers fournis (tâches 3 et 12).
# ---------------------------------------------------------------------------
rm -rf "${LAB_HOME}/examen"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/examen" "${LAB_HOME}/examen/inventaire"
cp "$FIX/kube-bench-job.yaml" "${LAB_HOME}/examen/"
cp "$FIX/Dockerfile" "${LAB_HOME}/examen/inventaire/Dockerfile"
chown -R "$LAB_USER:$LAB_USER" "${LAB_HOME}/examen"

# ---------------------------------------------------------------------------
# 6. L'état de départ de chaque tâche.
# ---------------------------------------------------------------------------
cat <<YAML | kubectl apply -f -
# Tâche 1 : quatre Pods qui se parlent librement.
apiVersion: v1
kind: Pod
metadata:
  name: db
  namespace: zone
  labels:
    app: db
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
  name: annuaire
  namespace: zone
  labels:
    app: annuaire
spec:
  containers:
    - name: service
      image: ${NGINX}
      ports:
        - containerPort: 80
---
apiVersion: v1
kind: Pod
metadata:
  name: web
  namespace: zone
  labels:
    app: web
spec:
  containers:
    - name: client
      image: ${BUSYBOX}
      command: ["sleep", "infinity"]
---
apiVersion: v1
kind: Pod
metadata:
  name: intrus
  namespace: zone
  labels:
    role: inconnu
spec:
  containers:
    - name: client
      image: ${BUSYBOX}
      command: ["sleep", "infinity"]
---
# Tâche 2 : un site publié sans TLS déclaré.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: site
  namespace: vitrine
spec:
  replicas: 1
  selector:
    matchLabels:
      app: site
  template:
    metadata:
      labels:
        app: site
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
  name: site
  namespace: vitrine
spec:
  selector:
    app: site
  ports:
    - port: 80
      targetPort: 80
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: site
  namespace: vitrine
spec:
  ingressClassName: traefik
  rules:
    - host: vitrine.lab
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: site
                port:
                  number: 80
---
# Tâche 4 : un compte de service administrateur du cluster.
apiVersion: v1
kind: ServiceAccount
metadata:
  name: dev-sa
  namespace: equipe-dev
---
apiVersion: v1
kind: Secret
metadata:
  name: jeton-de-paiement
  namespace: equipe-dev
type: Opaque
stringData:
  cle: "ce-que-dev-sa-ne-doit-plus-pouvoir-lire"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: portail-dev
  namespace: equipe-dev
spec:
  replicas: 1
  selector:
    matchLabels:
      app: portail-dev
  template:
    metadata:
      labels:
        app: portail-dev
    spec:
      serviceAccountName: dev-sa
      containers:
        - name: web
          image: ${NGINX}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: dev-admin-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
  - kind: ServiceAccount
    name: dev-sa
    namespace: equipe-dev
---
# Tâche 5 : une application qui porte un jeton d'API dont elle n'a pas l'usage.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: releveur
  namespace: releves
spec:
  replicas: 1
  selector:
    matchLabels:
      app: releveur
  template:
    metadata:
      labels:
        app: releveur
    spec:
      containers:
        - name: app
          image: ${BUSYBOX}
          command: ["sleep", "infinity"]
---
# Tâche 7 : le témoin, non confiné, sur le nœud du profil seccomp.
apiVersion: v1
kind: Pod
metadata:
  name: temoin
  namespace: confinement
spec:
  nodeName: k8s-cp.lab
  containers:
    - name: outil
      image: ${BUSYBOX}
      command: ["sleep", "infinity"]
---
# Tâche 8 : la preuve vivante que le namespace admet tout.
apiVersion: v1
kind: Pod
metadata:
  name: laxiste
  namespace: durci
spec:
  hostPID: true
  containers:
    - name: outil
      image: ${BUSYBOX}
      command: ["sleep", "infinity"]
      securityContext:
        runAsUser: 0
---
# Tâche 9 : un Pod qui cumule les défauts. Le tag flottant en est un, voulu.
apiVersion: v1
kind: Pod
metadata:
  name: insecure-app
  namespace: production
  labels:
    app: insecure-app
spec:
  hostPID: true
  containers:
    - name: app
      image: busybox:latest
      command: ["sh", "-c", "sleep 86400"]
      securityContext:
        privileged: true
        runAsUser: 0
        allowPrivilegeEscalation: true
---
# Tâche 10 : une clé d'API écrite en clair dans la spec.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: facturation
  namespace: tresor
spec:
  replicas: 1
  selector:
    matchLabels:
      app: facturation
  template:
    metadata:
      labels:
        app: facturation
    spec:
      containers:
        - name: app
          image: ${BUSYBOX}
          command: ["sleep", "infinity"]
          env:
            - name: CLE_API
              value: "cle-de-demonstration-7f3a"
---
# Tâche 11 : une image désignée par un tag.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pinned-app
  namespace: chaine
spec:
  replicas: 2
  selector:
    matchLabels:
      app: pinned-app
  template:
    metadata:
      labels:
        app: pinned-app
    spec:
      containers:
        - name: web
          image: nginx:1.30.5
          ports:
            - containerPort: 80
---
# Tâche 13 : le registre local, sur le port 5000 du control plane.
apiVersion: v1
kind: Pod
metadata:
  name: registre
  namespace: chaine-signature
  labels:
    app: registre
spec:
  nodeName: k8s-cp.lab
  hostNetwork: true
  containers:
    - name: registry
      image: ${REGISTRE}
      ports:
        - containerPort: 5000
          hostPort: 5000
---
# Tâche 14 : le Secret dont la lecture doit laisser une trace.
apiVersion: v1
kind: Secret
metadata:
  name: dossier-medical
  namespace: coffre
type: Opaque
stringData:
  numero: "ce-que-l-audit-doit-tracer"
---
# Tâche 15 : un site sans privilège, mais dont l'intérieur s'écrit encore.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vitrine
  namespace: catalogue
spec:
  replicas: 2
  selector:
    matchLabels:
      app: vitrine
  template:
    metadata:
      labels:
        app: vitrine
    spec:
      containers:
        - name: web
          image: ${NGINX_SANS_ROOT}
          ports:
            - containerPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: vitrine
  namespace: catalogue
spec:
  selector:
    app: vitrine
  ports:
    - port: 80
      targetPort: 8080
---
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: catalogue
spec:
  containers:
    - name: outil
      image: ${BUSYBOX}
      command: ["sleep", "infinity"]
YAML

# Tâche 16 : quatre Pods identiques sur le worker. Leurs specs ne diffèrent en
# rien : seul ce qui tourne DEDANS trahira celui qui est compromis.
for i in 1 2 3 4; do
cat <<YAML | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: atelier-${i}
  namespace: atelier
  labels:
    app: atelier
spec:
  nodeName: k8s-w1.lab
  containers:
    - name: outil
      image: ${BUSYBOX}
      command: ["sleep", "infinity"]
YAML
done

kubectl -n zone wait --for=condition=Ready pod/db pod/annuaire pod/web pod/intrus --timeout=240s
kubectl -n vitrine rollout status deployment/site --timeout=240s
kubectl -n equipe-dev rollout status deployment/portail-dev --timeout=240s
kubectl -n releves rollout status deployment/releveur --timeout=240s
kubectl -n confinement wait --for=condition=Ready pod/temoin --timeout=240s
kubectl -n durci wait --for=condition=Ready pod/laxiste --timeout=240s
kubectl -n production wait --for=condition=Ready pod/insecure-app --timeout=240s
kubectl -n tresor rollout status deployment/facturation --timeout=240s
kubectl -n chaine rollout status deployment/pinned-app --timeout=300s
kubectl -n chaine-signature wait --for=condition=Ready pod/registre --timeout=240s
kubectl -n catalogue rollout status deployment/vitrine --timeout=240s
kubectl -n catalogue wait --for=condition=Ready pod/client --timeout=240s
kubectl -n atelier wait --for=condition=Ready pod/atelier-1 pod/atelier-2 pod/atelier-3 pod/atelier-4 --timeout=240s

# ---------------------------------------------------------------------------
# 7. Tâche 13 : deux images dans le registre local, aucune signée.
# ---------------------------------------------------------------------------
for _ in $(seq 1 30); do
  curl -sf http://localhost:5000/v2/ >/dev/null 2>&1 && break
  sleep 2
done
curl -sf http://localhost:5000/v2/ >/dev/null
/usr/local/bin/crane copy "$BUSYBOX_138" localhost:5000/appli/web:1.0
/usr/local/bin/crane copy "$BUSYBOX_137" localhost:5000/appli/outil:1.0
/usr/local/bin/crane ls localhost:5000/appli/web
/usr/local/bin/crane ls localhost:5000/appli/outil

# ---------------------------------------------------------------------------
# 8. Ce que les outils doivent avoir sous la main, tiré MAINTENANT : le premier
#    audit et la première analyse ne doivent pas passer leur temps à télécharger.
# ---------------------------------------------------------------------------
crictl pull "$KUBE_BENCH" >/dev/null 2>&1 || true
/usr/local/bin/trivy config --quiet "${LAB_HOME}/examen/inventaire" >/dev/null 2>&1 || true

# ---------------------------------------------------------------------------
# 9. Tâche 16 : un processus de minage déguisé, lancé dans UN des quatre Pods.
#    Il est démarré par exec, pas par la spec : rien dans l'API ne le montre.
# ---------------------------------------------------------------------------
SUSPECT="atelier-$(( (RANDOM % 4) + 1 ))"
kubectl -n atelier exec "$SUSPECT" -- sh -c \
  'mkdir -p /tmp/.cache && printf "while :; do sleep 30; done\n" > /tmp/.cache/kdevtmpfsi && setsid sh /tmp/.cache/kdevtmpfsi </dev/null >/dev/null 2>&1 &'
sleep 2
PROCESSUS=$(kubectl -n atelier exec "$SUSPECT" -- ps)
[[ "$PROCESSUS" == *kdevtmpfsi* ]] || {
  echo "Le processus suspect ne tourne pas dans ${SUSPECT} : la tâche 16 n'a rien à trouver." >&2
  exit 1
}

# ---------------------------------------------------------------------------
# 10. Les gardes : chaque situation de départ est bien fausse.
# ---------------------------------------------------------------------------
kubectl get --raw /debug/pprof/ >/dev/null || {
  echo "Le profileur est déjà fermé : le socle a changé, la tâche 3 ne mesure plus rien." >&2
  exit 1
}
DB_IP=$(kubectl -n zone get pod db -o jsonpath='{.status.podIP}')
for _ in $(seq 1 20); do
  kubectl -n zone exec intrus -- wget -q -O /dev/null -T 3 "http://${DB_IP}/" && break
  sleep 3
done
kubectl -n zone exec intrus -- wget -q -O /dev/null -T 3 "http://${DB_IP}/"
kubectl -n chaine run sonde-depart --image=busybox:1.38.0 --restart=Never --dry-run=server -o name \
  --command -- sleep 5

echo "Examen posé : quatorze namespaces, seize tâches, chaque état de départ faux."
