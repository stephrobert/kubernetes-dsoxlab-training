# Changer de contexte et fixer le namespace par défaut

## La situation

Votre `kubectl` vise le cluster kind **`boutique`** par le contexte
**`kind-boutique`**. Votre fichier `~/.kube/config` connaît pourtant un second
cluster : le contexte **`recette`** y est déjà, à côté du premier. Aucun
namespace par défaut n'est réglé.

L'équipe vous demande de travailler désormais sur la recette, dans le namespace
**`kube-system`**, sans avoir à le répéter à chaque commande.

## Ce que vous devez obtenir

1. Le **contexte actif** est **`recette`**.

2. Le **namespace par défaut** du contexte `recette` est **`kube-system`**.

3. Une ConfigMap **`preuve`** existe, créée par une commande qui ne nomme **ni
   contexte ni namespace** : ni `--context`, ni `-n`. Elle doit se trouver dans
   `kube-system` du cluster de recette, et nulle part dans le cluster
   `boutique`.

## Les repères utiles

`kubectl config` lit et modifie votre kubeconfig : il sait lister les contextes,
dire lequel est actif, basculer de l'un à l'autre, et régler le namespace par
défaut du contexte courant. Il ne vérifie pas que ce namespace existe : relisez
ce que vous avez écrit.

La bascule est écrite dans le fichier, sous `current-context` : elle vaut pour
tous vos terminaux, et pour tous vos scripts. Une ConfigMap se crée en une
ligne, avec une valeur littérale.

## Comment vous saurez que c'est bon

Les tests lisent votre `~/.kube/config`, puis cherchent la ConfigMap `preuve`
dans les deux clusters. Elle n'atterrit au bon endroit que si la bascule et le
namespace par défaut sont justes.

```bash
dsoxlab check k8s-changer-de-contexte
```
