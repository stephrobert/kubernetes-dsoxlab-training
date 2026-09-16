#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
NS=zero-confiance

# 1. Fermer, dans les deux directions.
#
#    Un podSelector VIDE sélectionne tous les Pods du namespace. Déclarer une
#    direction sous policyTypes sans écrire la moindre règle pour elle, c'est
#    l'interdire entièrement ; ne pas la déclarer, c'est ne rien dire d'elle,
#    donc tout laisser passer. La nuance est toute la politique.
cat <<'YAML' | $K apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: zero-confiance
spec:
  podSelector: {}
  policyTypes:
    - Ingress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-egress
  namespace: zero-confiance
spec:
  podSelector: {}
  policyTypes:
    - Egress
YAML

# 2. Rouvrir le seul flux dont l'application a besoin.
#
#    Il faut les DEUX bouts : l'entrée de db, et la sortie de web. Deux
#    politiques par défaut ferment les deux extrémités du même flux, et n'en
#    rouvrir qu'une ne rétablit rien.
cat <<'YAML' | $K apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-web-to-db
  namespace: zero-confiance
spec:
  podSelector:
    matchLabels:
      app: db
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: web
      ports:
        - protocol: TCP
          port: 80
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-web-egress-to-db
  namespace: zero-confiance
spec:
  podSelector:
    matchLabels:
      app: web
  policyTypes:
    - Egress
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: db
      ports:
        - protocol: TCP
          port: 80
YAML

# 3. Rouvrir le DNS, et lui seul.
#
#    C'est le piège du lab : une sortie fermée par défaut coupe la résolution
#    de noms, et rien ne le signale. La règle vise le résolveur du cluster,
#    dans kube-system, sur le port 53 en UDP ET en TCP. Le namespaceSelector
#    et le podSelector sont dans le MÊME élément de la liste `to` : les
#    séparer autoriserait tout kube-system d'un côté, et tous les Pods
#    kube-dns du cluster de l'autre.
cat <<'YAML' | $K apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns-egress
  namespace: zero-confiance
spec:
  podSelector: {}
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
YAML
sleep 5

# 4. La preuve, flux par flux.
IP_DB=$($K -n "$NS" get pod db -o jsonpath='{.status.podIP}')
IP_ANNUAIRE=$($K -n "$NS" get pod annuaire -o jsonpath='{.status.podIP}')
echo -n "web -> db          : "
$K -n "$NS" exec web -- wget -qO- -T 4 "http://${IP_DB}/" >/dev/null && echo "passe" || echo "BLOQUÉ, anormal"
echo -n "intrus -> db       : "
$K -n "$NS" exec intrus -- wget -qO- -T 4 "http://${IP_DB}/" >/dev/null 2>&1 && echo "PASSE, anormal" || echo "bloqué"
echo -n "web -> annuaire    : "
$K -n "$NS" exec web -- wget -qO- -T 4 "http://${IP_ANNUAIRE}/" >/dev/null 2>&1 && echo "PASSE, anormal" || echo "bloqué"
echo -n "db -> annuaire     : "
$K -n "$NS" exec db -- wget -qO- -T 4 "http://${IP_ANNUAIRE}/" >/dev/null 2>&1 && echo "PASSE, anormal" || echo "bloqué"
echo -n "web résout un nom  : "
$K -n "$NS" exec web -- nslookup kubernetes.default.svc.cluster.local >/dev/null 2>&1 && echo "oui" || echo "NON, anormal"
echo "Le namespace est fermé, et seuls le flux prévu et le DNS passent."
