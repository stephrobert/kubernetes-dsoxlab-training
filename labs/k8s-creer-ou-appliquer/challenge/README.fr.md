# Challenge : Créer ou appliquer : apply, server-side apply et prune

## 📍 La situation

Le cluster kind **`lab`** tourne sur la machine, et votre kubectl le vise déjà.
Le namespace **`livraisons`** contient l'application **`suivi`**. Ses fichiers
sont dans le dossier **`~/livraisons/appli/`** : `suivi.yaml` à la racine, le
Service et la ConfigMap dans deux sous-dossiers. Jusqu'ici, seul `suivi.yaml`
a été appliqué.

- **`suivi`** tourne avec **4 réplicas**. C'est un autoscaler qui choisit ce
  nombre : il ne doit plus venir du fichier, qui écrit encore `replicas: 2`.
- **`suivi-ancien`** est une ConfigMap appliquée autrefois depuis ce dossier.
  Son fichier n'y est plus.
- **`journal`** est une ConfigMap appliquée depuis un autre dossier. Elle
  n'appartient pas à l'application `suivi`.
- **`tarifs`** est un Deployment créé par `kubectl create`. Il passe à l'équipe
  des tarifs, qui le pilote par server-side apply.

La version 2 de l'image :

```text
nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
```

## 🎯 Ce que vous devez obtenir

1. **Tout le dossier `~/livraisons/appli/` est appliqué**, sous-dossiers
   compris.
2. **`suivi.yaml` n'écrit plus `replicas`**, `suivi` garde ses **4 réplicas**,
   et **les garde aussi quand on réapplique le fichier**.
3. **`tarifs`** tourne en **version 2**, et son image appartient au
   gestionnaire de champs **`equipe-tarifs`**, par server-side apply.
4. **`suivi-ancien`** a été supprimée par élagage (`--prune`), et **`journal`**
   existe toujours, intacte.

## 🧭 Les repères utiles

`kubectl apply -f` sur un dossier ne lit pas les sous-dossiers, sauf si on le
lui demande.

Retirer un champ d'un fichier ne dit pas à `apply` de le laisser tel quel.
`apply` compare le fichier à l'annotation `last-applied-configuration` : un
champ qui a disparu du fichier est un champ à retirer. Regardez ce que fera
`apply` avant de le lancer, par exemple avec `--dry-run=server`.

Le server-side apply donne chaque champ à un gestionnaire. Prendre un champ
qu'un autre gestionnaire possède provoque un conflit, que la leçon explique.

`--prune` supprime ce qui n'est plus dans le dossier, parmi les objets qu'il
sélectionne. Simulez-le toujours avant de le lancer pour de bon.

## ✅ Comment vous saurez que c'est bon

Les tests lisent les annotations, simulent côté serveur un nouvel `apply` de
`suivi.yaml`, lisent les gestionnaires de champs de `tarifs`, et vérifient ce
que l'élagage a supprimé ou gardé.

```bash
dsoxlab check k8s-creer-ou-appliquer
```
