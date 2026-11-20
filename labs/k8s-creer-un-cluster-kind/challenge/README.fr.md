# Challenge : Créer un cluster kind multi-nœuds

## 📍 La situation

Sur la machine `k8s-kind.lab`, Docker, kind et kubectl sont installés, et
votre compte a le droit d'utiliser Docker. Pour vous laisser assez de mémoire,
**le lab a supprimé les clusters des autres labs** (`lab`, `boutique`,
`architecture`). Vous n'avez rien cassé : chaque lab recrée son cluster quand
vous le lancez. Le répertoire **`~/atelier/`** est vide.

## 🎯 Ce que vous devez obtenir

1. Un fichier **`~/atelier/kind-atelier.yaml`** qui décrit un cluster kind de
   **trois nœuds : un control plane et deux workers**.

2. Un cluster kind nommé **`atelier`**, créé à partir de ce fichier.

3. Ses **trois nœuds sont `Ready`**, en Kubernetes **`v1.37.0`**, avec l'image
   de nœud de la formation :
   `kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5`.

4. Les rôles sont justes : **un control plane et deux workers**.

## 🧭 Les repères utiles

Un cluster de plusieurs nœuds se décrit dans un fichier. La leçon en donne la
forme : une liste `nodes`, avec un `role` pour chaque nœud.

L'image du nœud se donne à `kind create cluster` avec `--image`, ou dans le
fichier, nœud par nœud, avec `image:`. Si vous donnez les deux, `--image`
l'emporte. La commande reçoit aussi le nom du cluster et le chemin du fichier.
Attention : sans nom, kind appelle le cluster `kind`.

Un cluster qui répond n'est pas forcément prêt. Comptez les nœuds et lisez les
colonnes `STATUS` et `VERSION` de `kubectl get nodes`. Attendez que les trois
soient `Ready`. Pour un worker, la colonne `ROLES` affiche `<none>` : c'est
normal.

## ✅ Comment vous saurez que c'est bon

Les tests lisent votre fichier, puis interrogent directement le cluster
`atelier`.

```bash
dsoxlab check k8s-creer-un-cluster-kind
```

`dsoxlab clean k8s-creer-un-cluster-kind` supprime ensuite le cluster
`atelier`.
