#!/usr/bin/env bash
# Pose la situation : l'application catalogue cassée par une mauvaise image,
# et le journal de 30 jours de la sonde de disponibilité.
#
# Le nombre de pannes et leur durée sont TIRÉS AU SORT, et gardés dans une
# mémoire lisible par root seulement : le SLI et le budget à trouver changent
# d'un passage à l'autre, et ne se recopient pas.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

NG='nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb'
MAUVAISE='nginx:1.30.5-introuvable'
MEMOIRE=/var/lib/dsoxlab/k8s-mesurer-un-slo-et-ecrire-un-runbook.json
JOURNAL=/srv/catalogue/sonde.csv
SESSION=$(getent passwd "${SUDO_USER:-ansible}" | cut -d: -f6)

for _ in $(seq 1 60); do
  kubectl get --raw /healthz >/dev/null 2>&1 && break
  sleep 3
done

# Repartir d'un état propre, même après un passage interrompu.
if kubectl get namespace catalogue >/dev/null 2>&1; then
  kubectl delete namespace catalogue --wait=true --timeout=180s
fi
rm -f "$SESSION/runbooks/catalogue-indisponible.sh"

kubectl create namespace catalogue
kubectl create deployment catalogue --image="$NG" --replicas=2 -n catalogue
kubectl expose deployment catalogue --port=80 -n catalogue
kubectl rollout status deployment/catalogue -n catalogue --timeout=180s
# Le déploiement fautif : une image qui n'existe pas. Révision 2, en échec.
kubectl set image deployment/catalogue nginx="$MAUVAISE" -n catalogue
kubectl annotate deployment catalogue -n catalogue kubernetes.io/change-cause="mise en production 2026-11-21" --overwrite

# Le journal de la sonde : une ligne par minute sur 30 jours, avec des pannes
# tirées au sort.
mkdir -p /srv/catalogue /var/lib/dsoxlab
python3 - "$JOURNAL" "$MEMOIRE" <<'PY'
import datetime, json, random, sys

journal, memoire = sys.argv[1], sys.argv[2]
total = 30 * 24 * 60
debut = datetime.datetime(2026, 10, 22, 0, 0, tzinfo=datetime.timezone.utc)
ko = set()
for _ in range(random.randint(3, 6)):
    duree = random.randint(15, 70)
    depart = random.randint(0, total - duree)
    ko.update(range(depart, depart + duree))
with open(journal, "w") as f:
    f.write("horodatage,statut\n")
    for m in range(total):
        t = debut + datetime.timedelta(minutes=m)
        f.write(f"{t:%Y-%m-%dT%H:%MZ},{'ko' if m in ko else 'ok'}\n")
json.dump({"total": total, "ko": len(ko)}, open(memoire, "w"))
print("minutes en panne :", len(ko))
PY
chmod 0644 "$JOURNAL"
chmod 0600 "$MEMOIRE"

echo "Situation posee : catalogue en panne (revision 2), journal de la sonde en $JOURNAL."
