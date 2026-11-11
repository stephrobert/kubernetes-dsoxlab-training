# Installer et configurer kubectl

## La situation

La machine `k8s-kind.lab` fait tourner un cluster kind, **`lab`**, en
Kubernetes **`v1.37.0`**, et votre fichier **`~/.kube/config`** pointe déjà
dessus. Vous n'avez pas à créer ce cluster : la leçon suivante vous apprendra à
le faire. Il vous manque l'outil pour lui parler, puisque **kubectl n'est pas
installé**, et aucune complétion n'est configurée.

## Ce que vous devez obtenir

1. **kubectl est installé dans `/usr/local/bin`**, appartient à `root`, est
   exécutable par tous et modifiable par root seul, et c'est lui que votre
   `PATH` trouve.

2. Le client est en **version 1.37**, épinglée. La leçon utilise la
   **`v1.37.2`**.

3. Le binaire installé est **le binaire officiel** de sa version : son
   empreinte est celle que publie `dl.k8s.io`, et vous l'avez vérifiée avant de
   l'installer.

4. La **complétion bash** de kubectl est active dans **chaque nouveau shell**.

5. L'**alias `k`** lance kubectl et se **complète** comme lui.

6. kubectl **atteint le serveur** du cluster.

## Les repères utiles

Ne téléchargez jamais « la dernière version » sans la nommer : une version
épinglée se réinstalle à l'identique, sur votre poste comme dans une CI. Le
client et le serveur peuvent différer d'**une version mineure au plus**, dans
un sens ou dans l'autre : un client 1.37 parle donc à ce cluster 1.37.0.

Une empreinte se vérifie **avant** d'installer, jamais après. Elle prouve que
le fichier reçu est bien celui que le projet a publié.

Ce que vous tapez dans votre shell disparaît à sa fermeture. Une complétion ou
un alias qui doit servir demain s'écrit dans un fichier que bash lit à chaque
démarrage. Pour vérifier, ouvrez un **nouveau** shell.

`kubectl version` affiche deux versions, celle du client et celle du serveur.
Si la seconde manque, kubectl n'a pas atteint le cluster.
`kubectl cluster-info` dit à quelle adresse il le cherche.

## Comment vous saurez que c'est bon

Les tests lisent le binaire installé, son empreinte, un nouveau shell
interactif et la réponse du serveur.

```bash
dsoxlab check k8s-installer-kubectl
```

`dsoxlab clean k8s-installer-kubectl` retire votre complétion et votre alias,
puis remet sur la machine le kubectl dont les labs suivants ont besoin.
