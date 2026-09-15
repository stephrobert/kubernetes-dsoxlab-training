# Entrer dans un conteneur sans shell avec kubectl debug

## La situation

Dans le namespace **`lab`**, une équipe fait tourner son propre résolveur
DNS, le Pod **`distroless-app`**. Son image est bâtie sur CoreDNS, et elle
est **distroless** : un seul binaire statique, ni shell, ni `ls`, ni `ps`.
C'est une bonne pratique de sécurité, jusqu'au jour où il faut regarder ce
qui se passe dedans. `kubectl exec` répond que `sh` n'existe pas, et les logs
ne disent rien de ce que fait le processus.

L'équipe vous demande deux choses. D'abord, obtenir la liste des processus qui
tournent **réellement** dans ce conteneur, vue de l'intérieur. Ensuite, un
cran plus bas : déposer un fichier témoin sur le nœud lui-même, **sans ouvrir
de session SSH**, comme on le ferait sur un nœud managé auquel personne n'a
d'accès direct.

## Ce que vous devez obtenir

1. Le Pod `distroless-app` porte un conteneur éphémère nommé **`debugger`**,
   qui partage l'espace des processus du conteneur `distroless-app`.

2. Depuis ce conteneur, la liste des processus a été écrite dans
   **`/tmp/debug-output.txt`** : on doit y lire le processus `coredns` de
   l'application. Le conteneur `debugger` **reste en vie**, pour qu'on puisse
   relire ce fichier.

3. Un Pod de débogage du nœud **`k8s-cp.lab`** existe et tourne, avec l'accès
   aux processus et au système de fichiers du nœud que `kubectl` lui donne.

4. Par ce Pod, le fichier **`/tmp/node-debug.txt`** a été écrit **sur le
   nœud lui-même**, avec le contenu `node-debug-ok`. Sur le nœud, pas dans
   le Pod.

## Les repères utiles

Un conteneur éphémère s'ajoute à un Pod qui tourne, sans le redémarrer, et
ne peut plus en être retiré. Il ne voit les processus d'un autre conteneur
que si on le lui demande explicitement.

Un Pod de débogage de nœud monte la racine du nœud sous un répertoire du Pod.
Ce qui est écrit dans `/tmp` du Pod disparaît avec lui ; ce qui est écrit
sous ce point de montage reste sur le nœud.

L'image d'outillage n'a pas d'importance, pourvu qu'elle ait un shell et
`ps` : busybox suffit.

## Comment vous saurez que c'est bon

Les tests lisent la définition du Pod, relisent le fichier dans le conteneur
`debugger`, cherchent un Pod qui a l'accès au nœud, et lisent
`/tmp/node-debug.txt` directement sur `k8s-cp.lab`.

```bash
dsoxlab check cka-kubectl-debug
```
