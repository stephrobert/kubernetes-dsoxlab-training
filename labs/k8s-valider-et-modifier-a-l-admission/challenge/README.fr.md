# Challenge : débloquer un namespace, puis valider et modifier à l'admission sans webhook

## 🧭 La situation

L'équipe des ateliers ne peut plus créer un seul Pod dans son namespace
**`ateliers`**. Chaque `kubectl run` ou `kubectl apply` y échoue. L'équipe
plateforme avait installé un contrôleur maison qui vérifiait les Pods de ce
namespace. Il a été désinstallé la semaine dernière.

Une fois le namespace débloqué, l'équipe plateforme veut deux règles, sans
remettre de contrôleur à faire tourner :

- tout Pod créé dans `ateliers` porte le label `equipe: ateliers`, même si son
  manifeste l'oublie ;
- aucun conteneur privilégié (`privileged: true`) n'est accepté dans
  `ateliers`.

Le namespace **`ateliers-temoin`** sert de témoin. Aucune des deux règles ne
doit s'y appliquer.

## 🎯 Ce que vous devez obtenir

1. Le webhook qui bloquait `ateliers` est **supprimé**, et un Pod ordinaire y
   est de nouveau accepté.
2. Un Pod soumis à `ateliers` **sans aucun label** en ressort avec le label
   `equipe=ateliers`. Un Pod d'`ateliers-temoin` ne le reçoit pas.
3. Dans `ateliers`, un Pod dont un conteneur est privilégié est **refusé** par
   une politique de l'API server. C'est vrai aussi quand le conteneur
   privilégié est un conteneur d'initialisation (`initContainers`). Un Pod
   ordinaire reste accepté, et un Pod privilégié reste accepté dans
   `ateliers-temoin`.

## 🔎 Les repères utiles

Commencez par lire le message d'erreur complet d'une création de Pod dans
`ateliers`. Il nomme le webhook et le Service qu'il appelle. Vérifiez ensuite
si ce Service a des Pods derrière lui.

Les deux règles se posent sans webhook ni contrôleur, avec les deux types de
policy natifs que montre la leçon : une politique qui modifie, une politique
qui valide. Chacune a besoin de sa liaison (binding) pour agir.

Pour tester une règle sans créer de Pod, ajoutez `--dry-run=server` à votre
commande : la requête passe par toute l'admission, mais rien n'est enregistré.

Laissez quelques secondes à l'API server après chaque changement avant de
conclure.

## ✅ Comment vous saurez que c'est bon

Les tests soumettent de vrais Pods à l'API server, en `--dry-run=server` : un
Pod sans label, un Pod privilégié, un Pod au conteneur d'initialisation
privilégié et un Pod ordinaire, dans les deux namespaces. Ils lisent ce que
l'API server accepte, refuse ou modifie.

```bash
dsoxlab check k8s-valider-et-modifier-a-l-admission
```
