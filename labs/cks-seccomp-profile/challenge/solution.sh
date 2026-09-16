#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
NS=confinement
PROFIL=/var/lib/kubelet/seccomp/profiles/restrict-chmod.json

# 1. Le profil, déposé sur le NŒUD. Ce n'est pas un objet Kubernetes : le
#    kubelet le lit sur le disque, dans un répertoire qu'il est seul à
#    connaître, et le chemin déclaré dans le Pod est RELATIF à
#    /var/lib/kubelet/seccomp.
#
#    defaultAction ALLOW laisse passer tout ce qui n'est pas nommé ; la règle
#    ERRNO refuse la famille chmod. Trois appels, et non un seul : `chmod`
#    emploie fchmodat sur une libc moderne, et ne filtrer que `chmod`
#    laisserait le conteneur changer les permissions sans être inquiété.
sudo mkdir -p "$(dirname "$PROFIL")"
sudo tee "$PROFIL" >/dev/null <<'JSON'
{
  "defaultAction": "SCMP_ACT_ALLOW",
  "syscalls": [
    {
      "names": ["chmod", "fchmod", "fchmodat"],
      "action": "SCMP_ACT_ERRNO"
    }
  ]
}
JSON

# 2. Le Pod qui s'en sert. Le type Localhost désigne un profil du nœud, et
#    localhostProfile porte le chemin relatif.
cat <<'YAML' | $K apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: seccomp-pod
  namespace: confinement
spec:
  nodeName: k8s-cp.lab
  securityContext:
    seccompProfile:
      type: Localhost
      localhostProfile: profiles/restrict-chmod.json
  containers:
    - name: outil
      image: busybox:1.37
      command: ["sh", "-c", "sleep 86400"]
YAML
$K -n "$NS" wait --for=condition=ready pod/seccomp-pod --timeout=180s

# 3. La preuve, des DEUX côtés. Un profil chargé et déclaré ne prouve rien :
#    un profil vide passerait les deux premières vérifications.
echo -n "ce qui doit rester permis (créer un fichier) : "
$K -n "$NS" exec seccomp-pod -- sh -c 'touch /tmp/preuve && echo "permis"'

echo -n "ce qui doit être refusé (chmod)               : "
if $K -n "$NS" exec seccomp-pod -- sh -c 'chmod 700 /tmp/preuve' 2>/dev/null; then
  echo "PASSE, anormal"
else
  echo "refusé, comme prévu"
fi

echo -n "le témoin, lui, peut toujours (chmod)         : "
$K -n "$NS" exec temoin -- sh -c 'touch /tmp/t && chmod 700 /tmp/t && echo "permis"'
echo "Le filtre agit sur le Pod confiné, et sur lui seul."
