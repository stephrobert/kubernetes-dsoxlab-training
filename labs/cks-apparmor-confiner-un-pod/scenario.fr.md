# Confiner un Pod avec un profil AppArmor

## La situation

Vous administrez un cluster sur lequel une équipe déploie un conteneur dont
vous ne maîtrisez pas le code. Vous voulez qu'il tourne, mais qu'il lui soit
**impossible d'écrire dans `/tmp`**, quoi que fasse le programme à l'intérieur.

Un `securityContext` classique ne répond pas à cette demande : il sait retirer
des capacités, forcer un utilisateur non root, rendre la racine en lecture
seule, mais il ne sait pas dire « ce processus n'écrira jamais dans ce
répertoire précis ». C'est le travail d'**AppArmor**, un module de sécurité du
noyau Linux.

Le profil est déjà déposé sur le control plane **`k8s-cp.lab`**, dans
`/etc/apparmor.d/k8s-refuser-ecriture`, et nulle part ailleurs. Il n'est
**pas chargé** : un fichier de profil posé sur le disque ne confine rien tant
que le noyau ne l'a pas lu. Et un profil chargé sur un nœud ne vaut que sur
ce nœud : le Pod devra tourner là où le profil est.

## Ce que vous devez obtenir

1. Le profil **`k8s-refuser-ecriture` est chargé** dans le noyau du nœud, en
   mode **enforce** et non en mode `complain`.

2. Un Pod nommé **`confine`** tourne dans le namespace **`confinement`**, sur
   le nœud où le profil est chargé, et son conteneur est **confiné par ce
   profil**.

3. Le confinement est **effectif** : une écriture dans `/tmp` depuis ce
   conteneur est refusée, alors que la lecture du système de fichiers
   fonctionne normalement.

## Les repères utiles

Sur le nœud, `aa-status` liste les profils chargés et leur mode. Un profil se
charge avec `apparmor_parser`, et le drapeau qui vous intéresse est celui qui
remplace un profil déjà présent.

Côté Kubernetes, le rattachement d'un profil à un conteneur se déclare **dans
le `securityContext`** depuis la 1.30. L'annotation
`container.apparmor.security.beta.kubernetes.io/<conteneur>` fonctionne encore
mais elle est obsolète, et l'examen attend la forme moderne.

Le nom du profil déclaré côté Kubernetes doit correspondre **exactement** à
celui que le noyau connaît, qui n'est pas le nom du fichier mais celui écrit
après le mot `profile` dans le fichier.

## Comment vous saurez que c'est bon

Le test vérifie l'état du **système**, pas les commandes que vous avez tapées :
il lit les profils chargés sur le nœud, la définition du Pod, et il tente
réellement une écriture dans le conteneur pour constater qu'elle est refusée.

```bash
dsoxlab check cks-apparmor-confiner-un-pod
```
