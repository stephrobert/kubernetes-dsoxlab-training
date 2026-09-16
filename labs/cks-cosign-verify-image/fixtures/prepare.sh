#!/usr/bin/env bash
# Pose la situation : un registre local qui porte deux images, aucune signee.
#
# Le registre est LOCAL, et ce n'est pas un raccourci. Signer une image suppose
# de POUSSER la signature a cote d'elle, dans le meme depot : aucun registre
# public ne le permettrait sans identifiants, et un lab qui demanderait un
# compte Docker Hub ne serait jouable par personne.
#
# Il tourne en hostNetwork sur le port 5000 du noeud, ce qui le rend joignable
# a l'adresse localhost:5000 depuis le noeud, la ou le candidat travaille.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace chaine-signature -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/chaine-signature --timeout=180s
fi
kubectl get namespace chaine-signature >/dev/null 2>&1 || kubectl create namespace chaine-signature

# Les cles d'un passage precedent sont retirees : sans cela, le candidat
# reprendrait une signature deja faite et le lab rendrait 100 avant le travail.
rm -f /root/cosign.key /root/cosign.pub
kubectl -n chaine-signature delete configmap cosign-pub-key --ignore-not-found --wait=true

kubectl -n chaine-signature delete pod registre --ignore-not-found --wait=true
kubectl apply -f - <<'YAML'
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
      image: registry:2
      ports:
        - containerPort: 5000
          hostPort: 5000
YAML
kubectl -n chaine-signature wait --for=condition=ready pod/registre --timeout=180s

# Le registre met un instant a ecouter apres que le Pod est Ready : on attend
# qu'il REPONDE, pas qu'il soit declare pret.
for _ in $(seq 1 30); do
  curl -sf http://localhost:5000/v2/ >/dev/null 2>&1 && break
  sleep 2
done
curl -sf http://localhost:5000/v2/ >/dev/null

# Les deux images, copiees telles quelles, sans aucune signature.
crane copy nginx:1.27-alpine localhost:5000/appli/web:1.0
crane copy busybox:1.37 localhost:5000/appli/outil:1.0
crane ls localhost:5000/appli/web
crane ls localhost:5000/appli/outil

echo "Situation posee : deux images dans le registre local, aucune signee."
