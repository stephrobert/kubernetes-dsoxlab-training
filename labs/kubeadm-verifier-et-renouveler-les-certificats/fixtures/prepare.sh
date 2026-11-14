#!/usr/bin/env bash
# Relève le numéro de série de chaque certificat du plan de contrôle et du
# certificat client d'admin.conf, de controller-manager.conf et de
# scheduler.conf, dans /var/lib/dsoxlab/pki-series.json : c'est
# la référence du renouvellement. Pose ensuite le fichier de réponses vide.
# Rejouable : le relevé est refait, il prend les certificats du moment.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x
LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
mkdir -p /var/lib/dsoxlab
python3 - <<'PY'
import base64, json, subprocess
def serie_pem(pem):
    return subprocess.run(["openssl", "x509", "-noout", "-serial"], input=pem, capture_output=True,
                          text=True, check=True).stdout.strip().split("=", 1)[1]
series = {}
for nom in ['apiserver', 'apiserver-kubelet-client', 'apiserver-etcd-client', 'front-proxy-client', 'etcd/server', 'etcd/peer', 'etcd/healthcheck-client']:
    series[nom] = serie_pem(open(f"/etc/kubernetes/pki/{nom}.crt").read())
import yaml
for conf in ("admin.conf", "controller-manager.conf", "scheduler.conf"):
    contenu = yaml.safe_load(open(f"/etc/kubernetes/{conf}"))
    pem = base64.b64decode(contenu["users"][0]["user"]["client-certificate-data"]).decode()
    series[conf] = serie_pem(pem)
json.dump(series, open("/var/lib/dsoxlab/pki-series.json", "w"), indent=2)
print(json.dumps(series, indent=2))
PY
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/pki"
cat > "${LAB_HOME}/pki/reponses.yaml" <<'YAML'
# La date d'échéance de l'autorité de certification du cluster (ca), au format
# AAAA-MM-JJ.
ca_expire_le: ""
YAML
chown -R "$LAB_USER:$LAB_USER" "${LAB_HOME}/pki"
echo "Lab posé : numéros de série relevés, ~/pki/reponses.yaml attend sa réponse."
