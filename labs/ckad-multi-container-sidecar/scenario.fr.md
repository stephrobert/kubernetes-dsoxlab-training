# Un sidecar natif qui suit les logs de l'application

## La situation

Une application ancienne, dans le namespace **`lab`**, n'écrit pas ses logs
sur la sortie standard : elle les écrit dans un fichier,
**`/var/log/app/output.log`**, une ligne par seconde. `kubectl logs` ne
montre donc rien, et l'équipe d'exploitation veut ces lignes là où tout le
monde les lit.

Plutôt que de modifier l'application, on lui adjoint un **sidecar** qui suit
le fichier et le recopie sur sa propre sortie standard. Un sidecar se
déclare d'une façon précise, qui garantit qu'il démarre
avant l'application et s'arrête après elle.

## Ce que vous devez obtenir

1. Un Pod **`app-with-sidecar`** dans `lab`, avec un volume **`logs`** de
   type `emptyDir`.

2. Un conteneur principal **`app`**, image `busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4`, qui écrit une
   ligne par seconde dans `/var/log/app/output.log`, sur ce volume.

3. Un **sidecar natif** nommé **`log-shipper`**, même image, déclaré comme
   il se doit, qui suit ce fichier en continu et le recopie
   sur sa sortie standard.

4. Le Pod tourne, le fichier se remplit, et `kubectl logs` du sidecar montre
   les lignes de l'application.

## Les repères utiles

Un sidecar natif n'est pas un second conteneur sous `containers` : c'est un
init container auquel on donne une `restartPolicy`. C'est ce détail qui
change tout, et c'est lui que l'examen attend.

Les deux conteneurs ne partagent rien par défaut, même pas un répertoire :
le volume doit être monté dans les deux.

## Comment vous saurez que c'est bon

Les tests lisent la définition du Pod, entrent dans le conteneur pour lire
le fichier, et lisent les logs du sidecar.

```bash
dsoxlab check ckad-multi-container-sidecar
```
