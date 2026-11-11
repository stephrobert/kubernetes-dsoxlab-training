# Créer ou appliquer : apply, server-side apply et prune

## La situation

Sur le cluster kind **`lab`**, que votre `kubectl` vise déjà, le namespace
**`livraisons`** porte l'application **`suivi`**, décrite dans le dossier
versionné **`~/livraisons/appli/`** : `suivi.yaml` à la racine, le Service et la
ConfigMap dans deux sous-dossiers. Seul `suivi.yaml` a été appliqué jusqu'ici.

- **`suivi`** tourne avec **4 réplicas** : c'est un autoscaler qui en décide, et
  ce nombre ne doit plus venir du fichier, qui fixe encore `replicas: 2`.
- **`suivi-ancien`**, une ConfigMap appliquée autrefois depuis ce dossier, n'y a
  plus de fichier.
- **`journal`**, une ConfigMap appliquée depuis un autre dossier, n'appartient pas
  à l'application `suivi`.
- **`tarifs`**, un Deployment créé par `kubectl create`, passe sous la
  responsabilité de l'équipe des tarifs, qui le pilote par server-side apply.

La version 2 de l'image :

```text
nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
```

## Ce que vous devez obtenir

1. **Tout le dossier `~/livraisons/appli/` est appliqué**, sous-dossiers compris.
2. **`suivi.yaml` ne fixe plus `replicas`**, `suivi` garde ses **4 réplicas**, et
   **réappliquer le fichier les garde** aussi.
3. **`tarifs`** tourne en **version 2**, et son image appartient au gestionnaire
   de champs **`equipe-tarifs`**, par server-side apply.
4. **`suivi-ancien`** a été retiré par élagage, et **`journal`** existe toujours,
   intact.

## Les repères utiles

`kubectl apply -f` sur un dossier ne descend pas dans les sous-dossiers sans le
demander.

Retirer un champ d'un fichier ne dit pas à `apply` de le laisser tranquille :
`apply` compare le fichier à l'annotation `last-applied-configuration`, et un
champ qui a disparu du fichier est un champ à retirer. Prévoyez ce que fera
`apply` avant de le lancer, par exemple avec `--dry-run=server`.

Le server-side apply attribue chaque champ à un gestionnaire. Reprendre un champ
qu'un autre possède provoque un conflit, que la leçon explique.

`--prune` supprime ce qui n'est plus dans le dossier, parmi ce qu'il sélectionne.
Prévisualisez-le toujours avant de le lancer pour de bon.

## Comment vous saurez que c'est bon

Les tests lisent les annotations, simulent un nouvel apply de `suivi.yaml` côté
serveur, lisent les gestionnaires de champs de `tarifs`, et vérifient ce que
l'élagage a retiré ou épargné.

```bash
dsoxlab check k8s-creer-ou-appliquer
```
