"""Fusionne les kubeconfig d'administration des deux clusters du lab.

Usage : fusion-kubeconfig.py <admin cluster-1> <admin cluster-2> <sortie> <utilisateur>

kubeadm nomme pareil le cluster, l'utilisateur et le contexte des deux
fichiers (kubernetes, kubernetes-admin, kubernetes-admin@kubernetes) : fusionnés
tels quels, le second écraserait le premier. Chaque nom reçoit donc le suffixe
de son cluster, et les contextes s'appellent cluster-1 et cluster-2, les noms
que le CLI cilium attend dans --context. Contexte courant : cluster-1.
"""
import os
import pwd
import sys
from pathlib import Path

import yaml

source1, source2, sortie, utilisateur = sys.argv[1:5]
fusion = {"apiVersion": "v1", "kind": "Config", "clusters": [], "users": [], "contexts": [],
          "current-context": "cluster-1", "preferences": {}}
for numero, chemin in ((1, source1), (2, source2)):
    conf = yaml.safe_load(Path(chemin).read_text())
    cluster, user = conf["clusters"][0], conf["users"][0]
    cluster["name"] = f"k8s-cluster-{numero}"
    user["name"] = f"admin-cluster-{numero}"
    fusion["clusters"].append(cluster)
    fusion["users"].append(user)
    fusion["contexts"].append({"name": f"cluster-{numero}",
                               "context": {"cluster": cluster["name"], "user": user["name"]}})

compte = pwd.getpwnam(utilisateur)
dossier = Path(sortie).parent
dossier.mkdir(mode=0o700, parents=True, exist_ok=True)
os.chown(dossier, compte.pw_uid, compte.pw_gid)
Path(sortie).write_text(yaml.safe_dump(fusion, sort_keys=False))
os.chmod(sortie, 0o600)
os.chown(sortie, compte.pw_uid, compte.pw_gid)
print(f"{sortie} : contextes cluster-1 et cluster-2")
