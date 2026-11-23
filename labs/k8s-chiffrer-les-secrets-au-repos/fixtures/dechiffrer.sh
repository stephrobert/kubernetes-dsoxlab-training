#!/usr/bin/env bash
# Ramene l'API server de k8s-cp.lab a son etat kubeadm d'origine, SANS perdre
# un seul Secret. Joue par prepare.sh (passage precedent) et par cleanup.yaml.
#
# Le piege que ce script evite : rendre le manifeste d'origine alors que des
# Secrets sont encore chiffres dans etcd. L'API server, qui n'a plus la cle,
# ne saurait plus les relire, et c'est le lab SUIVANT qui tomberait dessus
# (jetons, certificats d'un webhook, identifiants d'un registre). D'ou l'ordre
# impose par la documentation Kubernetes pour dechiffrer :
#
#   1. mettre `identity` EN PREMIER dans la configuration, en gardant les cles
#      pour pouvoir relire ;
#   2. relancer l'API server pour qu'il la relise ;
#   3. reecrire tous les objets concernes : ils repartent en clair ;
#   4. verifier dans etcd qu'aucune valeur ne porte plus le prefixe k8s:enc: ;
#   5. seulement alors, rendre le manifeste d'origine.
set -euo pipefail
# Trace sur le noeud, en AJOUT : appele par prepare.sh, ce script ne doit pas
# effacer le journal de celui-ci. Sa sortie remonte aussi dans ce journal-la.
exec > >(tee -a /var/log/dsoxlab-dechiffrer.log) 2>&1
set -x

MANIFESTE=/etc/kubernetes/manifests/kube-apiserver.yaml
SAUVEGARDE=/var/backups/kube-apiserver.avant-chiffrement.yaml
export KUBECONFIG=/etc/kubernetes/admin.conf
ETCD=(etcdctl --endpoints=https://127.0.0.1:2379
  --cacert=/etc/kubernetes/pki/etcd/ca.crt
  --cert=/etc/kubernetes/pki/etcd/server.crt
  --key=/etc/kubernetes/pki/etcd/server.key)

attendre_l_api() {
  local i
  for i in $(seq 1 60); do
    if kubectl get --raw /healthz >/dev/null 2>&1 \
      && [[ "$(kubectl -n kube-system get pods -l component=kube-apiserver \
               -o jsonpath='{.items[*].status.phase}' 2>/dev/null)" == "Running" ]]; then
      return 0
    fi
    sleep 3
  done
  echo "L'API server ne repond pas apres 3 minutes." >&2
  return 1
}

if ! grep -q -- '--encryption-provider-config=' "$MANIFESTE"; then
  echo "Aucun chiffrement configure : rien a dechiffrer."
  exit 0
fi

# Le fichier de configuration, vu depuis le NOEUD : le drapeau donne le chemin
# dans le conteneur, le volume hostPath dit ou il vit sur le disque.
read -r CONF RESSOURCES < <(python3 - "$MANIFESTE" <<'PY'
import sys, yaml
m = yaml.safe_load(open(sys.argv[1]))
c = m["spec"]["containers"][0]
chemin = next(a.split("=", 1)[1] for a in c["command"] if a.startswith("--encryption-provider-config="))
volumes = {v["name"]: v.get("hostPath", {}).get("path") for v in m["spec"].get("volumes", [])}
hote = chemin
for vm in c.get("volumeMounts", []):
    mp = vm["mountPath"].rstrip("/")
    if (chemin == mp or chemin.startswith(mp + "/")) and volumes.get(vm["name"]):
        hote = volumes[vm["name"]].rstrip("/") + chemin[len(mp):]
        break
conf = yaml.safe_load(open(hote))
ressources = sorted({r for bloc in conf.get("resources", []) for r in bloc.get("resources", [])})
print(hote, ",".join(ressources) or "secrets")
PY
)
echo "Configuration de chiffrement : $CONF (ressources : $RESSOURCES)"
if [[ ! -f "$SAUVEGARDE" ]]; then
  echo "Pas de sauvegarde $SAUVEGARDE : impossible de rendre le manifeste d'origine." >&2
  exit 1
fi

# 1. identity en premier, les cles gardees pour relire.
python3 - "$CONF" <<'PY'
import sys, yaml
chemin = sys.argv[1]
conf = yaml.safe_load(open(chemin))
for bloc in conf.get("resources", []):
    autres = [p for p in bloc.get("providers", []) if "identity" not in p]
    bloc["providers"] = [{"identity": {}}] + autres
open(chemin, "w").write(yaml.safe_dump(conf, sort_keys=False))
PY

# 2. Relancer l'API server : le kubelet recree le conteneur, qui relit le fichier.
crictl ps --name kube-apiserver -q | xargs -r crictl stop >/dev/null
sleep 10
attendre_l_api

# 3 et 4. Reecrire, puis verifier dans etcd. Un objet modifie pendant la
# reecriture rend un conflit : on recommence, dans un budget borne.
reste=1
for essai in 1 2 3 4 5; do
  for r in ${RESSOURCES//,/ }; do
    kubectl get "$r" -A -o json | kubectl replace -f - >/dev/null 2>&1 || true
  done
  reste=0
  for r in ${RESSOURCES//,/ }; do
    while read -r cle; do
      [[ -z "$cle" ]] && continue
      if "${ETCD[@]}" get "$cle" --print-value-only | head -c 8 | grep -q '^k8s:enc:'; then
        reste=$((reste + 1))
      fi
    done < <("${ETCD[@]}" get "/registry/$r/" --prefix --keys-only)
  done
  echo "Passage $essai : $reste valeur(s) encore chiffree(s)."
  [[ "$reste" -eq 0 ]] && break
  sleep 5
done
if [[ "$reste" -ne 0 ]]; then
  echo "Des valeurs restent chiffrees : le manifeste d'origine N'EST PAS rendu." >&2
  exit 1
fi

# 5. Le manifeste d'origine, maintenant que plus rien ne depend de la cle.
install -m 0600 "$SAUVEGARDE" "$MANIFESTE"
sleep 20
attendre_l_api
rm -f "$CONF"
echo "API server rendu a son etat d'origine, aucun Secret chiffre."
