# Réparer le réseau des Pods d'un nœud et lire ce que dit le réseau

## La situation

Sur le cluster kubeadm du catalogue, le worker **`k8s-w1.lab`** est passé
**NotReady** pendant la nuit. Le Pod **`cible`**, un nginx placé sur lui dans le
namespace **`reseau`**, reste en **`ContainerCreating`**. Sur le control plane,
le Pod **`sonde`** attend de pouvoir le joindre.

Deux Services du même namespace, **`stock`** et **`archives`**, ne répondent
pas non plus, mais chacun échoue à sa façon. L'équipe veut savoir lequel refuse
et lequel fait attendre.

Le CNI du cluster est **Calico**. Le répertoire **`~/reseau/`** est vide.

## Ce que vous devez obtenir

1. Dans **`~/reseau/plages.txt`**, une ligne **`pods: <plage>`** et une ligne
   **`services: <plage>`** : les plages d'adresses des Pods et des Services du
   **cluster entier**, telles que sa configuration les déclare.

2. Dans le même fichier, une ligne **`cible: <adresse>`** : l'adresse actuelle du
   Pod `cible`.

3. Le worker **`k8s-w1.lab`** est de nouveau **Ready**.

4. Le Pod **`cible`** tourne, **sur le worker**.

5. Le Pod **`sonde`**, sur le control plane, **joint `cible` par son adresse**,
   d'un nœud à l'autre.

6. Dans **`~/reseau/verdicts.txt`**, une ligne **`stock: refus`** ou
   **`stock: delai`**, et une ligne pour **`archives`** de la même forme : ce que
   fait réellement chacun des deux Services.

## Les repères utiles

Un nœud NotReady donne sa raison dans ses conditions. Un Pod bloqué en
`ContainerCreating` la donne dans ses événements. Les deux renvoient ici au même
endroit : la configuration CNI du nœud, sous `/etc/cni/net.d/`, sur le worker.

Ce fichier n'est pas écrit à la main : c'est le Pod du CNI, présent sur chaque
nœud, qui le pose à son démarrage. Un Pod d'un DaemonSet se recrée tout seul
quand on le supprime.

Avec Calico, le podCIDR inscrit sur un nœud ne dit **pas** d'où viennent les
adresses de ses Pods : Calico les tire de petits blocs du pool du cluster. La
plage qui compte est celle du cluster.

Une connexion refusée échoue **tout de suite**. Une connexion vers une adresse
qui ne répond pas **attend** jusqu'au délai fixé. Chronométrer une requête
suffit à les distinguer.

## Comment vous saurez que c'est bon

Chaque test vérifie un des six états ci-dessus. Le quatrième exige `cible` sur
le worker : le déplacer sur le control plane contournerait la panne sans la
réparer. Le sixième compare à un tirage au sort fait par la préparation : le bon
verdict ne se devine pas.

```bash
dsoxlab check cka-troubleshoot-networking
```
