# Créer un cluster kind multi-nœuds

## La situation

La machine `k8s-kind.lab` a Docker, kind et kubectl, et vous êtes dans le
groupe `docker`. **Pour vous laisser la mémoire nécessaire, le lab a supprimé
les clusters kind des autres labs** (`lab`, `boutique`, `architecture`) : vous
n'avez rien cassé, chaque lab recrée le sien quand vous le lancez. Le
répertoire **`~/atelier/`** est vide.

## Ce que vous devez obtenir

1. **`~/atelier/kind-atelier.yaml`** est un fichier de configuration kind qui
   décrit **un control plane et deux workers**.

2. Un cluster kind nommé **`atelier`** existe, créé depuis ce fichier.

3. Ses **trois nœuds sont Ready**, en Kubernetes **`v1.37.0`**, sur l'image de
   nœud épinglée de la formation :
   `kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5`.

4. Ses nœuds ont les bons rôles : un **control-plane** et deux **workers**.

## Les repères utiles

Un cluster multi-nœuds ne se décrit pas sur la ligne de commande : il se décrit
dans un fichier, que l'on versionne comme du code. La leçon en donne la forme,
avec une liste `nodes` dont chaque entrée porte un `role`.

L'image de nœud fixe la version de Kubernetes. Elle ne figure pas dans le
fichier : elle se passe à `kind create cluster`, avec le nom du cluster et le
chemin du fichier. Sans nom, kind crée un cluster nommé `kind`.

Un cluster qui répond n'est pas forcément prêt : comptez les nœuds, lisez leur
colonne STATUS et leur VERSION, et attendez qu'ils soient tous Ready. La colonne
ROLES d'un worker vaut `<none>`, c'est normal.

## Comment vous saurez que c'est bon

Les tests lisent votre fichier, puis interrogent le cluster `atelier`
directement.

```bash
dsoxlab check k8s-creer-un-cluster-kind
```

`dsoxlab clean k8s-creer-un-cluster-kind` supprime ensuite le cluster
`atelier`.
