#!/usr/bin/env bash
# Pose ~/interfaces/reponses.yaml, vide : les quatre réponses sont à trouver
# sur le nœud. Rejouable : un fichier d'un passage précédent est remplacé.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x
LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/interfaces"
cat > "${LAB_HOME}/interfaces/reponses.yaml" <<'YAML'
# Ce que vous lisez sur k8s-cp.lab. Remplacez chaque valeur vide.
#
# Le socket du runtime de conteneurs que le kubelet emploie, tel qu'il le
# déclare (par exemple unix:///chemin/vers/le.sock).
runtime_socket: ""
# Le runtime et sa version, tels que le nœud les annonce à l'API
# (par exemple nom://1.2.3).
runtime: ""
# Le nom du fichier de configuration CNI en vigueur dans /etc/cni/net.d.
cni_config: ""
# Le type du premier plugin de cette configuration.
cni_plugin: ""
# Les pilotes CSI enregistrés dans le cluster, un par ligne de liste.
csi_drivers: []
YAML
chown "$LAB_USER:$LAB_USER" "${LAB_HOME}/interfaces/reponses.yaml"
echo "Lab posé : ~/interfaces/reponses.yaml attend ses quatre réponses."
