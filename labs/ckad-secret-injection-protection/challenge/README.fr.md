# Challenge : Changer un mot de passe qui a fuité et le sortir du manifeste

## 📍 La situation

Vous êtes sur le control plane du cluster kubeadm, et votre kubectl est
configuré. Dans le namespace **`paiement`**, le Deployment **`passerelle`**
tourne. Il reçoit le mot de passe de sa base de données par la variable
d'environnement **`DATABASE_PASSWORD`**, dont la valeur est écrite **en clair
dans le manifeste**. Ce manifeste a été posé par `kubectl apply`.

Ce mot de passe a **fuité**. L'équipe de la base l'a révoqué et en a créé un
nouveau, que vous trouvez dans le fichier
**`~/paiement/nouveau-mot-de-passe.txt`**. Il change à chaque préparation du
lab : lisez-le dans ce fichier.

## 🎯 Ce que vous devez obtenir

1. Le **nouveau** mot de passe est rangé dans un **Secret** du namespace, comme
   valeur d'une de ses clés : relue et décodée, cette clé rend exactement le
   contenu du fichier. Le nom du Secret et celui de la clé sont à vous.

2. Ni l'ancien ni le nouveau mot de passe n'apparaît dans le manifeste du
   Deployment, tel que le rend `kubectl get deployment passerelle -o yaml`.

3. Aucun des deux n'est en clair dans un **ConfigMap** du namespace. Le
   déplacer vers un ConfigMap le ferait sortir du manifeste sans rien
   protéger.

4. L'application reçoit le nouveau mot de passe dans la variable
   **`DATABASE_PASSWORD`**, qui **tire sa valeur du Secret**, par référence.

5. Le même mot de passe est **aussi** disponible en **fichier**, dans le
   dossier `/etc/passerelle` du conteneur. Le volume doit désigner ce Secret
   et être monté à ce chemin exact.

6. Le Deployment tourne toujours : la mise à jour va au bout, et le Pod prêt
   est celui **né du manifeste modifié**, qui monte le Secret.

Modifiez ce qui existe. Le Deployment est **mis à jour sur place**, avec son
nom et son historique : le supprimer puis le recréer est refusé.

## 🧭 Les repères utiles

Créez le Secret à partir du fichier : le mot de passe ne passe alors ni dans
une commande, ni dans l'historique du shell. Le fichier n'a pas de retour à la
ligne final.

`kubectl apply` garde une copie du manifeste appliqué dans une annotation du
Deployment. Selon la façon dont vous modifiez le Deployment, cette copie suit
ou ne suit pas : relisez le manifeste entier après votre modification.

Un Pod qui demande un Secret absent, ou une clé qui n'y existe pas, **ne
démarre pas** : il reste en `CreateContainerConfigError`, et les événements du
Pod nomment ce qui manque.

## ✅ Comment vous saurez que c'est bon

Neuf tests, un par état demandé. Ils lisent le Deployment, le Secret décodé et
les ConfigMaps du namespace, puis ils entrent dans le conteneur pour vérifier
que l'application reçoit le nouveau mot de passe, par la variable et par le
fichier. Aucun ne passe sur la situation de départ.

```bash
dsoxlab check ckad-secret-injection-protection
```
