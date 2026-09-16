#!/usr/bin/env bash
# Pose la situation : un namespace qui n'applique aucun standard, et la preuve
# vivante qu'il n'en applique aucun.
#
# Le Pod `laxiste` est créé ICI, par le setup, et c'est délibéré. Il partage le
# namespace PID de l'hôte et tourne en root : sous le standard restricted, il
# serait refusé. Sa présence prouve à l'apprenant, avant qu'il ne touche à
# quoi que ce soit, que le namespace laisse tout passer.
#
# Il sert aussi de second instrument de mesure : une fois le standard activé,
# un Pod DÉJÀ créé continue de tourner. Pod Security Admission agit à
# l'admission, pas rétroactivement, et c'est une propriété que les candidats
# découvrent souvent le jour de l'examen.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne rend que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace secure-ns -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/secure-ns --timeout=180s
fi
kubectl get namespace secure-ns >/dev/null 2>&1 || kubectl create namespace secure-ns

# Le namespace repart SANS aucun label de standard : c'est le travail de
# l'apprenant, et un passage précédent a pu les poser.
for mode in enforce warn audit; do
  kubectl label namespace secure-ns "pod-security.kubernetes.io/${mode}-" --overwrite >/dev/null 2>&1 || true
  kubectl label namespace secure-ns "pod-security.kubernetes.io/${mode}-version-" --overwrite >/dev/null 2>&1 || true
done

# Ce que l'apprenant doit produire est retiré s'il traîne.
kubectl -n secure-ns delete pod conforme --ignore-not-found --wait=true

# Le Pod qui ne passerait pas le standard restricted, créé pendant qu'il n'y a
# pas de standard. hostPID et root : deux violations, pour que le message de
# refus soit parlant quand l'apprenant le tentera à nouveau.
kubectl -n secure-ns delete pod laxiste --ignore-not-found --wait=true
kubectl -n secure-ns apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: laxiste
  namespace: secure-ns
spec:
  hostPID: true
  containers:
    - name: outil
      image: busybox:1.37
      command: ["sh", "-c", "sleep 86400"]
      securityContext:
        runAsUser: 0
YAML

kubectl -n secure-ns wait --for=condition=ready pod/laxiste --timeout=180s

echo "Situation posée : secure-ns n'applique aucun standard, et laxiste le prouve."
