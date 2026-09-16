#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
MANIFESTE=/etc/kubernetes/manifests/kube-apiserver.yaml
POLITIQUE=/etc/kubernetes/audit-policy.yaml
JOURNAL=/var/log/kubernetes/audit.log

attendre_l_api() {
  for _ in $(seq 1 80); do
    $K get --raw /healthz >/dev/null 2>&1 && return 0
    sleep 3
  done
  echo "L'API server ne répond plus." >&2
  return 1
}

# 1. La politique. L'ordre des règles compte : l'API server retient la
#    PREMIÈRE qui correspond, donc la règle attrape-tout doit venir en
#    dernier, sinon elle avalerait les Secrets avec.
sudo tee "$POLITIQUE" >/dev/null <<'YAML'
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  - level: RequestResponse
    resources:
      - group: ""
        resources: ["secrets"]
  - level: Metadata
YAML
sudo mkdir -p "$(dirname "$JOURNAL")"

# 2. Les flags, et les volumes qui vont avec. C'est le point où l'on se
#    trompe : l'API server est un Pod, il ne voit du nœud que ce qu'on lui
#    monte. Des flags sans volumes donnent un conteneur qui boucle sur
#    « no such file or directory ».
sudo python3 - "$MANIFESTE" <<'PY'
import sys, pathlib, yaml

chemin = pathlib.Path(sys.argv[1])
manifeste = yaml.safe_load(chemin.read_text(encoding="utf-8"))
conteneur = manifeste["spec"]["containers"][0]

flags = [
    "--audit-policy-file=/etc/kubernetes/audit-policy.yaml",
    "--audit-log-path=/var/log/kubernetes/audit.log",
    "--audit-log-maxage=7",
    "--audit-log-maxbackup=2",
]
for flag in flags:
    nom = flag.split("=")[0]
    conteneur["command"] = [c for c in conteneur["command"] if not c.startswith(nom + "=")]
    conteneur["command"].append(flag)

montages = {
    "audit-policy": ("/etc/kubernetes/audit-policy.yaml", "File"),
    "audit-log": ("/var/log/kubernetes", "DirectoryOrCreate"),
}
conteneur.setdefault("volumeMounts", [])
manifeste["spec"].setdefault("volumes", [])
for nom, (chemin_hote, type_hote) in montages.items():
    conteneur["volumeMounts"] = [m for m in conteneur["volumeMounts"] if m["name"] != nom]
    manifeste["spec"]["volumes"] = [v for v in manifeste["spec"]["volumes"] if v["name"] != nom]
    conteneur["volumeMounts"].append(
        {"name": nom, "mountPath": chemin_hote, "readOnly": nom == "audit-policy"}
    )
    manifeste["spec"]["volumes"].append(
        {"name": nom, "hostPath": {"path": chemin_hote, "type": type_hote}}
    )

chemin.write_text(yaml.safe_dump(manifeste, default_flow_style=False), encoding="utf-8")
print("manifeste réécrit avec les flags et les volumes d'audit")
PY

# Le kubelet voit le manifeste changer et redéploie le Pod. L'API disparaît
# quelques secondes : c'est normal, et c'est pourquoi on attend.
sleep 10
attendre_l_api

# 3. La preuve : on lit un Secret, puis on relit ce que le cluster a écrit.
$K -n coffre get secret dossier-medical >/dev/null
sleep 5

echo "--- une lecture de Secret, au niveau RequestResponse ---"
sudo grep -m1 '"resource":"secrets"' "$JOURNAL" | head -c 400; echo
echo "--- une lecture banale, au niveau Metadata seulement ---"
sudo grep -m1 '"resource":"pods"' "$JOURNAL" | head -c 300; echo

echo "L'audit distingue les Secrets du reste, et le journal le prouve."
