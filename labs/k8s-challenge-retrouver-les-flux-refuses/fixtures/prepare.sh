#!/usr/bin/env bash
# Pose la situation du challenge sur le cluster Cilium du socle (net-*).
#
# Namespace livraison : deux destinations, stock sur net-w1.lab et tarif sur
# net-w2.lab, et quatre clients qui appellent les deux toutes les deux
# secondes, deux par worker. Un client, tiré au sort, porte le profil
# restreint : une NetworkPolicy de SORTIE ne lui laisse joindre que l'une des
# deux destinations, tirée au sort elle aussi. Le refus se produit donc au
# départ, sur l'agent Cilium du nœud du client, et non sur celui de la
# destination.
#
# Namespace voisin : un autre refus permanent, sans rapport avec livraison.
# Un journal qui ne filtre que sur le verdict l'embarque.
#
# Seul root lit la référence (source, destination, nœud).
# Rejouable : les deux namespaces sont recréés à neuf.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

REFERENCE=/var/lib/dsoxlab-labs/k8s-challenge-retrouver-les-flux-refuses.json
NGINX=nginx:1.30.6
BUSYBOX=busybox:1.38.0

for ns in livraison voisin; do
  if kubectl get namespace "$ns" >/dev/null 2>&1; then
    kubectl delete namespace "$ns" --wait=true --timeout=180s
  fi
  kubectl create namespace "$ns"
done

SOURCE="$(shuf -n 1 -e preparation expedition facturation retours)"
REFUSEE="$(shuf -n 1 -e stock tarif)"
if [[ "$REFUSEE" == stock ]]; then PERMISE=tarif; else PERMISE=stock; fi
declare -A NOEUD=([preparation]=net-w1.lab [expedition]=net-w2.lab [facturation]=net-w1.lab [retours]=net-w2.lab)

mkdir -p /var/lib/dsoxlab-labs
install -m 0600 /dev/null "$REFERENCE"
printf '{"source": "%s", "destination": "%s", "noeud": "%s", "permise": "%s"}\n' \
  "$SOURCE" "$REFUSEE" "${NOEUD[$SOURCE]}" "$PERMISE" > "$REFERENCE"

for dest in stock tarif; do
  if [[ "$dest" == stock ]]; then noeud=net-w1.lab; else noeud=net-w2.lab; fi
  kubectl apply -f - <<YAML
apiVersion: v1
kind: Pod
metadata:
  name: ${dest}
  namespace: livraison
  labels:
    app: ${dest}
spec:
  nodeName: ${noeud}
  containers:
    - name: ${dest}
      image: ${NGINX}
      ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: ${dest}
  namespace: livraison
spec:
  selector:
    app: ${dest}
  ports:
    - port: 80
      targetPort: 80
YAML
done

for client in preparation expedition facturation retours; do
  if [[ "$client" == "$SOURCE" ]]; then profil=restreint; else profil=standard; fi
  kubectl apply -f - <<YAML
apiVersion: v1
kind: Pod
metadata:
  name: ${client}
  namespace: livraison
  labels:
    role: client
    profil: ${profil}
spec:
  nodeName: ${NOEUD[$client]}
  containers:
    - name: client
      image: ${BUSYBOX}
      command:
        - sh
        - -c
        - while true; do for d in stock tarif; do wget -q -T 2 -O /dev/null http://\$d.livraison.svc.cluster.local/ || true; done; sleep 2; done
YAML
done

kubectl apply -f - <<YAML
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: profil-restreint
  namespace: livraison
spec:
  podSelector:
    matchLabels:
      profil: restreint
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
    - to:
        - podSelector:
            matchLabels:
              app: ${PERMISE}
      ports:
        - protocol: TCP
          port: 80
YAML

# Le voisin : une cible fermée à tous, et une sonde qui insiste.
kubectl apply -f - <<YAML
apiVersion: v1
kind: Pod
metadata:
  name: cible
  namespace: voisin
  labels:
    app: cible
spec:
  nodeName: ${NOEUD[$SOURCE]}
  containers:
    - name: cible
      image: ${NGINX}
---
apiVersion: v1
kind: Service
metadata:
  name: cible
  namespace: voisin
spec:
  selector:
    app: cible
  ports:
    - port: 80
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tout-fermer
  namespace: voisin
spec:
  podSelector:
    matchLabels:
      app: cible
  policyTypes:
    - Ingress
---
apiVersion: v1
kind: Pod
metadata:
  name: sonde
  namespace: voisin
spec:
  nodeName: ${NOEUD[$SOURCE]}
  containers:
    - name: sonde
      image: ${BUSYBOX}
      command:
        - sh
        - -c
        - while true; do wget -q -T 2 -O /dev/null http://cible.voisin.svc.cluster.local/ || true; sleep 2; done
YAML

kubectl -n livraison wait --for=condition=Ready pod --all --timeout=180s
kubectl -n voisin wait --for=condition=Ready pod --all --timeout=180s
kubectl -n livraison get pods -o wide
echo "Situation posée : un flux de livraison refusé à la sortie, un refus voisin."
