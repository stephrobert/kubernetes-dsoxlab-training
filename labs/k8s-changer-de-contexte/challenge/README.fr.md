# Challenge : Changer de contexte et fixer le namespace par défaut

## 📍 La situation

Votre kubectl vise le cluster kind **`boutique`**, par le contexte
**`kind-boutique`**. Votre fichier `~/.kube/config` connaît aussi un second
cluster, par le contexte **`recette`**. Aucun namespace par défaut n'est fixé.

L'équipe vous demande de travailler désormais sur la recette, dans le
namespace **`kube-system`**, sans avoir à le préciser à chaque commande.

## 🎯 Ce que vous devez obtenir

1. Le **contexte utilisé** est **`recette`**.

2. Le **namespace par défaut** du contexte `recette` est **`kube-system`**.

3. Une ConfigMap **`preuve`** existe. Créez-la avec une commande qui ne
   précise **ni contexte ni namespace** : pas de `--context`, pas de `-n`.
   Elle doit se trouver dans `kube-system`, sur le cluster de recette, et nulle
   part sur le cluster `boutique`.

4. Votre **`~/.kube/config`** n'est lisible et modifiable **que par vous**. Il
   contient de quoi agir sur les deux clusters, et aujourd'hui ses droits,
   `-rw-r--r--`, laissent tous les comptes de la machine le lire : seuls les
   répertoires qui le contiennent le protègent, et une copie ailleurs serait
   lisible par tous.

## 🧭 Les repères utiles

Toutes les commandes utiles commencent par `kubectl config` : lister les
contextes, voir celui qui est utilisé, changer de contexte, fixer le namespace
du contexte utilisé. Attention : kubectl ne vérifie pas que le namespace
existe. Relisez ce que vous avez tapé.

Le changement de contexte est enregistré dans le fichier : il vaut pour tous
vos terminaux. Une ConfigMap se crée en une ligne, avec une valeur écrite
directement dans la commande (`--from-literal`).

## ✅ Comment vous saurez que c'est bon

Les tests lisent votre `~/.kube/config` et ses droits, puis cherchent la
ConfigMap `preuve` sur les deux clusters. Elle n'est au bon endroit que si le
contexte et le namespace sont justes.

```bash
dsoxlab check k8s-changer-de-contexte
```
