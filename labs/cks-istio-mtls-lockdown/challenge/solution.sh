#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -eu

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
CIBLE=http://service.maillage.svc.cluster.local/

# 1. Constater l'état de départ : le client sans sidecar passe.
echo -n "avant, client nu -> service : "
$K -n dehors exec client-nu -- wget -qO- -T 4 "$CIBLE" >/dev/null 2>&1 \
  && echo "passe" || echo "bloqué"

# 2. L'exigence. Une PeerAuthentication en mode STRICT dans le namespace
#    impose le TLS mutuel à TOUS ses Pods : le trafic en clair est refusé,
#    quelle qu'en soit la provenance.
#
#    Le mode PERMISSIVE, qui est celui par défaut, accepte les deux et ne
#    protège de rien : il sert aux migrations, pas aux productions.
cat <<'YAML' | $K apply -f -
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: strict
  namespace: maillage
spec:
  mtls:
    mode: STRICT
YAML

# La règle descend jusqu'aux sidecars par istiod : elle n'est pas immédiate.
sleep 20

# 3. La preuve, dans les deux sens.
echo -n "après, client maillé -> service : "
$K -n maillage exec client-maille -c outil -- wget -qO- -T 4 "$CIBLE" >/dev/null 2>&1 \
  && echo "passe" || echo "BLOQUÉ, anormal"
echo -n "après, client nu     -> service : "
$K -n dehors exec client-nu -- wget -qO- -T 4 "$CIBLE" >/dev/null 2>&1 \
  && echo "PASSE, anormal" || echo "bloqué"
echo "Le maillage n'accepte plus que ses propres membres."
