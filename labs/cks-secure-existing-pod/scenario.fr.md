# Reprendre un Pod privilégié en production, sans le priver de son travail

## La situation

Dans le namespace **`production`**, le Pod **`insecure-app`** tourne depuis
des semaines. Il fonctionne, personne ne s'en plaint, et c'est bien le
problème : il a été créé dans l'urgence avec tout ce qu'il fallait pour que
« ça marche ».

Un audit vient de le signaler. À vous de le reprendre.

## Ce que vous devez obtenir

1. Un Pod **`secure-app`** dans `production`, qui fait le même travail que
   l'original et qui **tourne**.

2. Il ne conserve **aucun** des défauts de `insecure-app`. Ils sont plusieurs,
   et les trouver fait partie de l'exercice : lisez la définition complète de
   l'original avant d'écrire quoi que ce soit.

3. L'image est épinglée sur une **version**, et non sur un nom qui peut
   changer sous vous au prochain redémarrage.

4. **`insecure-app` n'existe plus.** Un correctif posé à côté de la faille ne
   corrige rien.

## Les repères utiles

`kubectl get pod insecure-app -o yaml` rend la définition complète, y compris
ce que vous n'avez pas écrit. C'est là que se lisent les partages de namespace
avec l'hôte, les privilèges et l'identité du processus.

Le `securityContext` existe à deux niveaux, et tous les champs ne sont pas
acceptés aux deux : ce qui concerne l'utilisateur vaut au niveau du Pod comme
du conteneur, tandis que le privilège, l'escalade et les capacités ne se
déclarent qu'au niveau du conteneur.

Un conteneur privilégié reçoit **toutes** les capacités du noyau. Les retirer
une à une n'a pas de sens : on les retire toutes, puis on rend celles dont
l'application a besoin, et une application qui dort n'en a besoin d'aucune.

## Comment vous saurez que c'est bon

Les tests lisent la définition du nouveau Pod, vérifient que l'ancien a
disparu, puis entrent dans le conteneur. Le dernier est le seul qui prouve
quelque chose : il **compte** les processus que le conteneur voit. Avec le
namespace de l'hôte, il en voit plus d'une centaine, ceux du nœud entier ;
sans lui, une poignée.

```bash
dsoxlab check cks-secure-existing-pod
```
