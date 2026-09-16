# Rendre un conteneur immuable sans le faire tomber

## La situation

Dans le namespace **`catalogue`**, le Deployment **`vitrine`** sert une page à
deux exemplaires. Il tourne déjà sous un utilisateur non privilégié, ce que
l'équipe a considéré comme suffisant.

Ce ne l'est pas. Depuis l'intérieur du conteneur, l'image ouvre à son propre
utilisateur des chemins dans lesquels il est possible d'écrire, y compris sa
configuration. Un attaquant qui obtient l'exécution de code dans ce conteneur
peut donc y déposer ce qu'il veut, et ce qu'il dépose survit à son passage.

Un Pod **`client`** est là pour interroger le service depuis le cluster.

## Ce que vous devez obtenir

1. Le système de fichiers du conteneur n'est plus inscriptible.

2. Le conteneur ne peut plus obtenir de privilèges supplémentaires, et il ne
   conserve **aucune** capacité du noyau.

3. Le processus ne tourne pas sous l'identité de l'administrateur, et le
   cluster le sait.

4. **Le site répond toujours.** C'est la moitié difficile : une application
   qui écrit pendant son démarrage ne redémarre pas dans un système de
   fichiers fermé.

Modifiez ce qui existe. Ne remplacez pas le Deployment par un objet d'un autre
nom.

## Les repères utiles

Fermer le système de fichiers ferme **tout** ce que porte l'image. Ce qui doit
rester inscriptible se rouvre chemin par chemin.

Ne devinez pas quels chemins : l'application le dit. Quand un Pod ne remonte
pas, son journal nomme le premier fichier sur lequel il a buté.

Les chemins rouverts n'ont pas à survivre au redémarrage du conteneur : il
s'agit de cache et de fichiers temporaires. Le type de volume qui convient est
celui dont le contenu est perdu avec le Pod.

Tous les champs ne vivent pas au même niveau : ce qui concerne l'identité du
processus s'accepte au niveau du Pod comme du conteneur, tandis que l'escalade,
les capacités et le système de fichiers ne s'acceptent qu'au niveau du
conteneur.

Un Pod existant ne change pas de `securityContext`. C'est le Deployment qui se
modifie, et ses Pods qui se recréent.

## Comment vous saurez que c'est bon

Le dernier test exerce **les deux côtés** : il tente une écriture depuis
l'intérieur du conteneur, qui doit être refusée, puis interroge le service
depuis le Pod `client`, qui doit répondre. Les deux sont dans le même test :
« le site répond » est déjà vrai avant votre intervention, et un nginx qui ne
démarre plus n'écrit nulle part non plus.

```bash
dsoxlab check cks-security-context-immutable
```
