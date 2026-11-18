#!/usr/bin/env bash
# Le routeur FRR 10.6.2 du lab k8s-annoncer-un-service-en-bgp, HORS du cluster
# net-* : sur l'hôte témoin (k8s-cp.lab), dans un espace de noms réseau à lui,
# derrière une interface macvlan d'adresse propre. L'hôte témoin fait déjà du
# BGP pour Calico (BIRD écoute sur le port 179) : partager sa pile réseau
# mettrait les deux démons sur le même port.
#
#   routeur.sh present <adresse/masque> <ASN du routeur> <ASN du cluster> <voisin> [<voisin>...]
#   routeur.sh absent
#
# Image épinglée par digest, lancée par ctr (containerd est déjà sur l'hôte),
# dans une unité systemd transitoire : rien ne redémarre seul au boot.
set -euo pipefail
# La trace complète va dans un journal de l'hôte témoin : dsoxlab ne rend que
# « non-zero return code » quand ce script échoue.
exec > >(tee /var/log/dsoxlab-routeur-frr.log) 2>&1

ETAT=$1; shift
IMAGE="quay.io/frrouting/frr@sha256:89e5e1ec8b17c5dffaf57dbac58a29ebeb3731a84e5bc09dad1662adff2ba7f5"
NS=dsoxlab-frr
UNITE=dsoxlab-routeur-frr
CONF=/etc/dsoxlab-frr
CTR="ctr -n dsoxlab"

arreter() {
  systemctl stop "$UNITE" 2>/dev/null || true
  systemctl reset-failed "$UNITE" 2>/dev/null || true
  $CTR task kill -s SIGKILL routeur-frr 2>/dev/null || true
  sleep 1
  $CTR task rm -f routeur-frr 2>/dev/null || true
  $CTR container rm routeur-frr 2>/dev/null || true
  ip netns del "$NS" 2>/dev/null || true
}

if [ "$ETAT" = absent ]; then
  arreter
  rm -rf "$CONF" /run/dsoxlab-frr
  echo "routeur FRR retiré"
  exit 0
fi

ADRESSE=$1; ASN=$2; ASN_CLUSTER=$3; shift 3
VOISINS=("$@")
INTERFACE=$(ip -o -4 route show default | awk '{print $5; exit}')
PASSERELLE=$(ip -o -4 route show default | awk '{print $3; exit}')

arreter

install -d -m 0755 "$CONF"
cat > "$CONF/daemons" <<'EOF'
bgpd=yes
zebra=yes
vtysh_enable=yes
zebra_options="  -A 127.0.0.1 -s 90000000"
bgpd_options="   -A 127.0.0.1"
EOF
{
  echo "frr defaults traditional"
  echo "hostname routeur-frr"
  echo "log stdout informational"
  echo "!"
  echo "router bgp $ASN"
  echo " bgp router-id ${ADRESSE%/*}"
  echo " no bgp ebgp-requires-policy"
  echo " neighbor CLUSTER peer-group"
  echo " neighbor CLUSTER remote-as $ASN_CLUSTER"
  for v in "${VOISINS[@]}"; do echo " neighbor $v peer-group CLUSTER"; done
  echo " !"
  echo " address-family ipv4 unicast"
  echo "  neighbor CLUSTER activate"
  echo " exit-address-family"
  echo "!"
} > "$CONF/frr.conf"

ip netns add "$NS"
ip link add frr0 link "$INTERFACE" type macvlan mode bridge
ip link set frr0 netns "$NS"
ip netns exec "$NS" ip link set lo up
ip netns exec "$NS" ip addr add "$ADRESSE" dev frr0
ip netns exec "$NS" ip link set frr0 up
ip netns exec "$NS" ip route add default via "$PASSERELLE"

# Docker crée /var/run/frr à la volée, ctr non : sans lui, watchfrr s'arrête
# sur « Can't create pid lock file » (mesuré le 2026-11-17).
install -d -m 0777 /run/dsoxlab-frr
$CTR image pull "$IMAGE" > /dev/null
systemd-run --unit "$UNITE" $CTR run --rm --privileged \
  --with-ns "network:/var/run/netns/$NS" \
  --mount "type=bind,src=/run/dsoxlab-frr,dst=/var/run/frr,options=rbind:rw" \
  --mount "type=bind,src=$CONF/daemons,dst=/etc/frr/daemons,options=rbind:ro" \
  --mount "type=bind,src=$CONF/frr.conf,dst=/etc/frr/frr.conf,options=rbind:ro" \
  "$IMAGE" routeur-frr

for i in $(seq 1 30); do
  if $CTR task exec --exec-id "pret-$i" routeur-frr vtysh -c 'show bgp summary' > /dev/null 2>&1; then
    $CTR task exec --exec-id version routeur-frr vtysh -c 'show version' | head -1
    echo "routeur FRR prêt à ${ADRESSE%/*}, ASN $ASN, voisins ${VOISINS[*]}"
    exit 0
  fi
  sleep 2
done
echo "le routeur FRR ne répond pas" >&2
journalctl -u "$UNITE" --no-pager | tail -20 >&2
exit 1
