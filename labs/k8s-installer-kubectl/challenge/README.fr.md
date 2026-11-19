# Challenge : Installer et configurer kubectl

## 📍 La situation

La machine `k8s-kind.lab` fait tourner un cluster kind, **`lab`**, en
Kubernetes **`v1.37.0`**, et votre fichier **`~/.kube/config`** pointe déjà
dessus. Vous n'avez pas à créer ce cluster : la leçon suivante vous apprendra à
le faire. Il vous manque l'outil pour lui parler, puisque **kubectl n'est pas
installé**, et aucune complétion n'est configurée.

## 🎯 Ce que vous devez obtenir

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

## 🧭 Les repères utiles

Écrivez le numéro de version dans vos commandes, par exemple `v1.37.2`. Ne
prenez pas « la dernière version » sans savoir laquelle c'est : demain, ce ne
sera plus la même. Le client kubectl peut avoir une version mineure d'écart
avec le cluster, pas plus. Un kubectl 1.37 convient donc à ce cluster en
1.37.0.

Vérifiez l'empreinte du binaire **avant** de l'installer. Si elle ne
correspond pas, le fichier téléchargé n'est pas celui que le projet a publié :
supprimez-le et recommencez.

Une commande tapée dans le terminal est oubliée quand vous le fermez. Pour
garder l'alias et la complétion, écrivez-les dans `~/.bashrc` : bash lit ce
fichier à chaque ouverture. Ouvrez ensuite un **nouveau** terminal pour
vérifier. Sous Debian, la complétion de kubectl a aussi besoin du paquet
`bash-completion`. Sans lui, la touche Tab ne propose que des noms de
fichiers.

Pour savoir si kubectl atteint le cluster, lancez `kubectl version`. La ligne
`Server Version` doit apparaître. Si elle manque, `kubectl cluster-info` vous
montre à quelle adresse kubectl cherche le cluster.

## ✅ Comment vous saurez que c'est bon

Les tests lisent le binaire installé, son empreinte, un nouveau shell
interactif et la réponse du serveur.

```bash
dsoxlab check k8s-installer-kubectl
```

`dsoxlab clean k8s-installer-kubectl` retire votre complétion et votre alias,
puis remet sur la machine le kubectl dont les labs suivants ont besoin.
