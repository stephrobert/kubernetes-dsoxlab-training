# Atteindre une application : expose et port-forward

## La situation

Le cluster kind **`boutique`** tourne sur la machine, et votre `kubectl` le vise
déjà. Dans le namespace **`acces`**, le Deployment **`echo`** fait tourner deux
Pods agnhost qui écoutent sur le **port 8080**. Sur le chemin `/hostname`,
chaque Pod répond son propre nom. Aucun Service ne les expose encore.

Le relevé **`~/acces/releve.txt`** attend ce que vous lirez à travers le tunnel.

## Ce que vous devez obtenir

1. Un Service **`echo`** expose le Deployment sur le **port 80**, vers le
   **port 8080** des Pods.

2. Le Service compte les **deux Pods** comme endpoints prêts.

3. Un tunnel **`kubectl port-forward` vers le Service** `echo` écoute sur le
   port local **`18080`**, et il est **toujours ouvert** quand vous lancez la
   vérification.

4. **`pod-du-tunnel`** donne le nom du Pod qui vous répond à travers **ce**
   tunnel.

## Les repères utiles

`kubectl expose` fait plusieurs choses à votre place : il copie le sélecteur du
Deployment, et sans `--target-port` il reprend la valeur de `--port`. Générez
d'abord le manifeste sans rien créer pour vérifier ce qu'il va écrire.

Un tunnel `kubectl port-forward` est un processus, pas un objet : il vit tant
que la commande tourne. Lancez-le en arrière-plan avec sa sortie dans un
journal, interrogez-le depuis la machine, et laissez-le tourner jusqu'à la
vérification : le correcteur passe lui-même par lui. Les ports se lisent
« local, puis distant ». Vers un Service, le tunnel s'attache à un seul Pod,
choisi au lancement.

## Comment vous saurez que c'est bon

Les tests lisent le Service et ses EndpointSlices, cherchent votre tunnel parmi
les processus de la machine, font une requête par le port 18080, et comparent
votre relevé au Pod qui y répond. Un nom recopié depuis `kubectl get pods` ne
suffit pas.

```bash
dsoxlab check k8s-atteindre-une-application
```
