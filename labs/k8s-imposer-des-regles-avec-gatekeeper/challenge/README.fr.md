# Challenge : installer Gatekeeper, imposer une règle et lire son audit

## 🧭 La situation

L'équipe entrepôt ne doit plus faire tourner que des images venues du registre
**`registry.k8s.io/`**. La règle doit vivre dans le cluster, et l'équipe
sécurité a choisi **Gatekeeper**, en version **v3.23.1**. Il n'est pas encore
installé.

Dans le namespace **`entrepot`**, le Pod **`ancien-stock`** tourne déjà avec
une image de Docker Hub. L'équipe veut le voir apparaître dans un rapport
avant de le migrer : **ne le supprimez pas**.

Le namespace **`entrepot-temoin`** sert de témoin. La règle ne doit pas s'y
appliquer.

## 🎯 Ce que vous devez obtenir

1. Gatekeeper **v3.23.1** tourne dans le namespace `gatekeeper-system`, avec
   son contrôleur et son audit prêts.
2. Dans `entrepot`, un Pod dont l'image ne commence pas par
   `registry.k8s.io/` est **refusé** à la création par Gatekeeper. Un Pod dont
   l'image vient de `registry.k8s.io/` reste accepté, et `entrepot-temoin`
   accepte toujours une image de Docker Hub.
3. L'**audit** de Gatekeeper relève `ancien-stock` comme une violation de
   votre règle.

## 🔎 Les repères utiles

La leçon donne l'installation par le manifeste de la release : gardez la
version épinglée dans l'URL.

Gatekeeper sépare la règle en deux objets. Le premier contient la logique en
Rego, et crée un nouveau type de ressource. Le second applique ce type à un
périmètre, avec ses paramètres. La leçon montre un exemple de registres
autorisés : lisez bien comment il compare le début du nom de l'image.

Le mode de la contrainte décide de ce qui arrive à un Pod fautif : un seul
des trois modes le refuse.

L'admission ne contrôle que les nouvelles requêtes. Pour un Pod qui tournait
déjà, regardez le `status` de votre contrainte : l'audit y écrit ce qu'il
trouve, une fois par minute.

## ✅ Comment vous saurez que c'est bon

Les tests lisent les Deployments de Gatekeeper et leur image. Ils soumettent
ensuite de vrais Pods à l'API server, en `--dry-run=server`, avec une image de
Docker Hub et une image de `registry.k8s.io/`, dans les deux namespaces. Ils
lisent enfin le `status` de vos contraintes pour y trouver `ancien-stock`.

```bash
dsoxlab check k8s-imposer-des-regles-avec-gatekeeper
```
