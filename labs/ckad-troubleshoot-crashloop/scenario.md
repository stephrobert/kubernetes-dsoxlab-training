# Trois Pods en CrashLoopBackOff, trois causes

## La situation

Dans le namespace **`lab`**, trois Pods redémarrent en boucle depuis ce
matin : **`bad-command`**, **`missing-env`** et **`oom-killed`**. Leurs noms
ne sont pas un indice, c'est l'équipe précédente qui les a nommés ainsi
après coup, en découvrant les pannes, et personne ne les a corrigés.

Chacun meurt pour une raison différente, et chaque raison se lit à un
endroit différent : le message de sortie du conteneur, ses logs, ou ce que
le kubelet raconte de sa dernière mort.

## Ce que vous devez obtenir

1. `bad-command` tourne : sa commande de démarrage existe et reste en vie.

2. `missing-env` tourne : il reçoit la variable d'environnement qu'il exige.
   Ses logs disent laquelle.

3. `oom-killed` tourne : sa limite de mémoire suffit à nginx, au moins
   **64Mi**, et il n'est plus tué par le noyau.

4. Les trois Pods sont en **`Running`**, stables, et le compteur de
   redémarrages ne monte plus.

## Les repères utiles

`kubectl describe pod` montre pour chaque conteneur son dernier état
terminé, avec une raison, `Error` ou `OOMKilled`, et un code de sortie.
`kubectl logs --previous` montre ce que le conteneur a écrit avant de
mourir.

Un Pod nu ne se modifie pas sur ces champs : la commande, les variables et
les limites sont figées. Il faut le recréer, avec le même nom.

## Comment vous saurez que c'est bon

Les tests lisent l'état de chaque Pod, sa limite de mémoire, et s'assurent
que le compteur de redémarrages n'augmente plus.

```bash
dsoxlab check ckad-troubleshoot-crashloop
```
