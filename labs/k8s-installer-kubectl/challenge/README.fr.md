# Challenge : Installer et configurer kubectl

## 📍 La situation

Sur la machine `k8s-kind.lab`, un cluster kind nommé **`lab`** tourne, en
Kubernetes **`v1.37.0`**. Votre fichier **`~/.kube/config`** sait déjà s'y
connecter. Vous n'avez pas à créer ce cluster : c'est le sujet de la leçon
suivante. Il vous manque seulement l'outil pour lui parler : **kubectl n'est
pas installé**, et sa complétion non plus.

## 🎯 Ce que vous devez obtenir

1. **kubectl est installé dans `/usr/local/bin`.** Le fichier appartient à
   `root`. Tout le monde peut le lancer, mais seul `root` peut le modifier.
   C'est lui que le shell trouve quand vous tapez `kubectl`.

2. kubectl est en **version 1.37**. La leçon utilise la **`v1.37.2`**.

3. C'est **le fichier officiel** : son empreinte est celle que publie
   `dl.k8s.io`. Vérifiez-la avant d'installer.

4. La **complétion** de kubectl marche dans **chaque nouveau terminal**.

5. L'**alias `k`** lance kubectl, et la touche Tab le complète comme kubectl.

6. kubectl **joint le cluster**.

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

Les tests regardent le fichier installé, son empreinte, ce que voit un nouveau
terminal, et la réponse du cluster.

```bash
dsoxlab check k8s-installer-kubectl
```

`dsoxlab clean k8s-installer-kubectl` retire ensuite votre alias et votre
complétion, et remet sur la machine le kubectl dont les labs suivants ont
besoin.
