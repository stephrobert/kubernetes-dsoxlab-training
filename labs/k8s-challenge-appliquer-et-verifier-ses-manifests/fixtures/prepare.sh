#!/usr/bin/env bash
# Pose la situation : aucun objet de l'application annuaire, un répertoire de
# travail ~/annuaire vide, et le cahier des charges. Le délai avant qu'un
# exemplaire neuf soit compté disponible est TIRÉ AU SORT : il se lit dans le
# cahier, et c'est à l'apprenant de trouver le champ d'API qui le porte.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

MEMOIRE=/var/lib/dsoxlab/challenge-appliquer-et-verifier-ses-manifests.json
MAISON=$(getent passwd "${LAB_USER:-ansible}" | cut -d: -f6)
DOSSIER="$MAISON/annuaire"

for ns in annuaire-recette annuaire-production; do
  kubectl delete namespace "$ns" --ignore-not-found --wait=true --timeout=180s
done
rm -rf "$DOSSIER"
install -d -o "${LAB_USER:-ansible}" -g "${LAB_USER:-ansible}" "$DOSSIER"

DELAI=$(python3 -c 'import random; print(random.randint(8, 20))')
mkdir -p /var/lib/dsoxlab
printf '{"delai": %s}\n' "$DELAI" > "$MEMOIRE"
chmod 0600 "$MEMOIRE"

cat > "$DOSSIER/cahier-des-charges.txt" <<EOF
Cahier des charges de l'application annuaire

- Le serveur : l'image nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb,
  qui sert sur le port 80.
- Plusieurs exemplaires, gérés et remplacés automatiquement par le cluster :
  un seul en recette, trois en production.
- Les autres applications du cluster joignent l'annuaire sous le nom
  « annuaire », sur le port 8080.
- Un exemplaire neuf n'est compté comme disponible qu'après $DELAI secondes
  sans plantage.
- Deux variantes : recette (namespace annuaire-recette) et production
  (namespace annuaire-production). Chaque variante crée son namespace.
EOF
chown "${LAB_USER:-ansible}:" "$DOSSIER/cahier-des-charges.txt"

echo "Situation posee : cahier des charges en $DOSSIER, delai de $DELAI s."
