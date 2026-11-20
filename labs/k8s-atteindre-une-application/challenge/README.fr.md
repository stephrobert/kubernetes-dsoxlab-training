# Challenge : Atteindre une application : expose et port-forward

## 📍 La situation

Le cluster kind **`boutique`** tourne sur la machine, et votre kubectl le vise
déjà. Dans le namespace **`guichet`**, le Deployment **`annonces`** fait
tourner deux Pods agnhost qui écoutent sur le **port 9376**. Sur le chemin
`/hostname`, chaque Pod répond son propre nom. Aucun Service ne les expose
encore.

Le fichier **`~/guichet/releve.txt`** attend ce que vous lirez à travers le
tunnel.

## 🎯 Ce que vous devez obtenir

1. Un Service **`annonces`** expose le Deployment sur le **port 8081**, vers le
   **port 9376** des Pods.

2. Le Service compte les **deux Pods** comme endpoints prêts.

3. Un tunnel **`kubectl port-forward` vers le Service** `annonces` écoute sur
   le port local **`19081`**. Il est **toujours ouvert** quand vous lancez la
   vérification.

4. Après **`pod-du-tunnel`**, dans le fichier : le nom du Pod qui vous répond à
   travers **ce** tunnel.

## 🧭 Les repères utiles

`kubectl expose` choisit des valeurs à votre place : il copie le sélecteur du
Deployment, et sans `--target-port`, il reprend la valeur de `--port`. Regardez
d'abord le manifeste qu'il écrirait, sans rien créer.

Un tunnel `kubectl port-forward` est un processus, pas un objet : il vit tant
que la commande tourne. Lancez-le en arrière-plan, avec ses messages dans un
journal, interrogez-le depuis la machine, et laissez-le tourner jusqu'à la
vérification : le correcteur passe lui-même par lui. Les ports se lisent
« local, puis distant ». Vers un Service, le tunnel s'attache à un seul Pod,
choisi au lancement.

## ✅ Comment vous saurez que c'est bon

Les tests lisent le Service et ses EndpointSlices. Ils cherchent votre tunnel
parmi les processus de la machine, envoient une requête par le port 19081, et
comparent votre fichier au Pod qui répond. Un nom recopié depuis
`kubectl get pods` ne suffit pas.

```bash
dsoxlab check k8s-atteindre-une-application
```
