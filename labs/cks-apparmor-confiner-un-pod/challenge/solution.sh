#!/usr/bin/env bash
# Solution du formateur. Elle sert à la validation en intégration : rejouée
# avant les tests, elle prouve que le lab est FAISABLE et que ses tests
# passent quand le travail est fait. Un lab dont la solution échoue est un lab
# cassé, et c'est le seul moyen de s'en apercevoir avant l'apprenant.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Charger le profil dans le noyau. -r remplace s'il est déjà là, ce qui
#    rend le script rejouable.
sudo apparmor_parser -r /etc/apparmor.d/k8s-refuser-ecriture

# 2. Poser le Pod, profil rattaché par le champ typé de la 1.30.
$K delete pod confine -n confinement --ignore-not-found --wait=true >/dev/null 2>&1 || true
cat <<'YAML' | $K apply -n confinement -f -
apiVersion: v1
kind: Pod
metadata:
  name: confine
spec:
  containers:
    - name: app
      image: busybox:1.37.0@sha256:f85340bf132ae937d2c2a763b8335c9bab35d6e8293f70f606b9c6178d84f42b
      command: ["sh", "-c", "sleep 3600"]
      securityContext:
        appArmorProfile:
          type: Localhost
          localhostProfile: k8s-refuser-ecriture
YAML

$K wait --for=condition=Ready pod/confine -n confinement --timeout=120s
