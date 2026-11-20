# Challenge : Réparer un Service NodePort

## 📍 La situation

Vous êtes sur le control plane du cluster kubeadm, et votre kubectl est
configuré. Dans le namespace **`guichet`**, l'application **`accueil`** tourne
en deux Pods. Chacun répond son nom, `accueil`, sur le port de son conteneur.

Pour que des utilisateurs hors du cluster la joignent, un collègue a écrit un
Service **`accueil`** de type NodePort. Pourtant, personne ne la joint.

Le cluster compte deux nœuds, **`k8s-cp.lab`** et **`k8s-w1.lab`**.

## 🎯 Ce que vous devez obtenir

1. Le Service `accueil` est de type **NodePort**, et son port de nœud vaut
   **`30091`** : c'est l'adresse promise aux utilisateurs.

2. Ses **endpoints** sont les Pods prêts du Deployment `accueil`, joints sur le
   **port où leur conteneur écoute**.

3. `http://<adresse de k8s-cp.lab>:30091/` répond **`accueil`**.

4. `http://<adresse de k8s-w1.lab>:30091/` répond **`accueil`** aussi.

## 🧭 Les repères utiles

Un Service, c'est un sélecteur et des ports. Pas d'endpoint : le sélecteur ne
correspond aux labels d'aucun Pod. Des endpoints, mais rien ne répond : c'est
souvent le port vers lequel il envoie.

Un Service NodePort a **trois** ports : celui du Service dans le cluster, celui
du conteneur vers lequel il envoie, et celui qu'il ouvre sur **chaque nœud**.
Si on ne le donne pas, Kubernetes tire ce dernier au hasard dans sa plage.

L'adresse de chaque nœud se lit dans la colonne `INTERNAL-IP` de
`kubectl get nodes -o wide`.

## ✅ Comment vous saurez que c'est bon

Chaque test vérifie une des quatre exigences ci-dessus. Les deux derniers envoient
une vraie requête, l'un au control plane, l'autre au worker : un NodePort
s'ouvre sur tous les nœuds, où que tournent les Pods.

```bash
dsoxlab check ckad-service-nodeport-reparer
```
