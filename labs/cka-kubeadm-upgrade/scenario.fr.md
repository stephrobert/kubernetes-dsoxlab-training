# Monter un cluster d'une version mineure, sans interrompre ce qui tourne

## La situation

Le cluster est en retard d'une **version mineure**. La direction technique a
tranché : la montée se fait cette semaine, et l'application de supervision, qui
tourne dans le namespace **`supervision`**, ne doit pas cesser de répondre pendant
l'opération.

Elle s'appelle **`sonde`** et tourne en deux exemplaires, répartis sur les
nœuds.

## Ce que vous devez obtenir

1. L'API server annonce la version **v1.37.0**.

2. **Chaque nœud** annonce cette même version, control plane et worker compris.

3. **Aucun nœud n'est laissé inordonnançable.**

4. L'application `sonde` a toujours ses **deux** exemplaires prêts.

Tous les paquets nécessaires sont disponibles sur les nœuds : vous n'avez pas
de dépôt à déclarer.

## Les repères utiles

L'ordre n'est pas une préférence : **le plan de contrôle d'abord**, les nœuds
ensuite. Un worker ne peut pas dépasser son plan de contrôle.

Sur le plan de contrôle, l'outil qui conduit la montée doit **lui-même** être à
la version visée avant de l'appliquer, sinon il ne sait pas ce qu'elle attend.

Les paquets Kubernetes sont **figés** sur ces nœuds : il faut les libérer pour
les changer, et les refiger ensuite.

Le piège le plus fréquent : la commande qui applique la version au cluster **ne
monte pas le kubelet**. Elle s'occupe des composants du plan de contrôle, pas du
service qui tourne sur chaque machine.

Sur un worker, la commande **n'est pas la même** que sur le plan de contrôle.

Videz un nœud avant d'y toucher, pour que ses Pods aillent ailleurs plutôt que
de disparaître avec lui. Et **rendez-le** ensuite : un nœud vidé reste
inordonnançable tant qu'on ne l'a pas rendu, et le cluster tourne alors avec un
nœud en moins sans que rien ne le signale.

Le worker se joint depuis le plan de contrôle par `ssh k8s-w1.lab`.

## Comment vous saurez que c'est bon

Le dernier test lit la version de **chaque** nœud, vérifie qu'aucun n'est resté
inordonnançable, et que l'application a toujours ses deux exemplaires. Les trois
sont dans le même test : monter le plan de contrôle en oubliant un nœud laisse
un cluster qui fonctionne et qui est pourtant faux.

```bash
dsoxlab check cka-kubeadm-upgrade
```
