# Challenge : Exposer un Deployment par un Service ClusterIP

## 📍 La situation

Vous êtes sur le control plane du cluster kubeadm, et votre kubectl est
configuré. Dans le namespace **`lab`**, l'équipe veut un serveur web en **trois
exemplaires**. Les autres applications du cluster doivent le joindre sous un
nom stable, **`web-svc`**, quel que soit le Pod qui répond. Pour vérifier que
les requêtes se répartissent, chaque Pod doit répondre **son propre nom**.

Un Pod **`client`** est là pour interroger le Service. Il sert à mesurer le
résultat : laissez-le en place. Si vous le supprimez,
`dsoxlab reset ckad-expose-service` le remet.

## 🎯 Ce que vous devez obtenir

1. Un Deployment **`web`** dans `lab`, avec **trois Pods** et l'image
   **`busybox:1.38.0`**. Chaque Pod sert **son propre nom d'hôte** en HTTP sur
   le port **8080**, et porte le label **`app=web`**. Les trois Pods doivent
   être **disponibles** : un conteneur dont la commande se termine tout de
   suite redémarre en boucle et ne devient jamais disponible.

2. Un Service **`web-svc`** de type **ClusterIP**, sur le port **80**, qui
   envoie vers le port **8080** des Pods `app=web`. Le port cible peut s'écrire
   avec le numéro `8080`, ou avec le **nom d'un `containerPort` qui vaut
   8080** : les deux sont acceptés.

3. Le Service a **exactement trois endpoints prêts**. Aucun autre Pod du
   namespace ne doit porter le label `app=web`, sinon il entre lui aussi dans
   le Service et fait un quatrième endpoint.

4. Depuis `client`, `http://web-svc/` répond à **dix requêtes sur dix**. Chaque
   réponse est le nom d'un **Pod qui existe vraiment**, et **au moins deux Pods
   différents** répondent sur ces dix requêtes. Chaque Pod est aussi interrogé
   sur son propre `127.0.0.1:8080`, et doit répondre **son propre nom** : un
   nom inventé, même s'il ressemble à un nom de Pod, est refusé.

## 🧭 Les repères utiles

Un serveur qui répond son nom d'hôte tient en une commande busybox : écrire la
sortie de `hostname` dans un fichier, puis servir le répertoire avec `httpd`.
Trois options comptent :

- **`-f`** : rester au premier plan, sinon le conteneur s'arrête ;
- **`-p 8080`** : le port demandé, `httpd` écoutant sur 80 par défaut ;
- **`-h <répertoire>`** : le répertoire à servir.

Dans un Pod, le nom d'hôte est le nom du Pod.

`kubectl expose deployment` crée le Service en une commande, si vous lui donnez
le port et le port cible.

## ✅ Comment vous saurez que c'est bon

Onze critères, un par exigence ci-dessus : le Deployment et ses Pods, le
Service et ses endpoints, puis dix requêtes depuis `client` et une requête
directe à chaque Pod.

```bash
dsoxlab check ckad-expose-service
```
