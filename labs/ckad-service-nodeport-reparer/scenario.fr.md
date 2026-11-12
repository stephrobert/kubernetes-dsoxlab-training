# Réparer un Service NodePort

## La situation

Dans le namespace **`guichet`**, l'application **`accueil`** tourne en deux
réplicas, et chacun de ses Pods répond son nom, `accueil`, sur son port de
conteneur. Pour que des utilisateurs hors du cluster la joignent, un collègue a
écrit un Service **`accueil`** de type NodePort. Personne ne la joint pourtant.

Le cluster compte deux nœuds, **`k8s-cp.lab`** et **`k8s-w1.lab`**.

## Ce que vous devez obtenir

1. Le Service `accueil` est de type **NodePort**, et son NodePort vaut
   **`30091`**, l'adresse promise aux utilisateurs.

2. Ses **endpoints** sont les Pods prêts du Deployment `accueil`, joints sur le
   **port où leur conteneur écoute**.

3. `http://<adresse de k8s-cp.lab>:30091/` répond **`accueil`**.

4. `http://<adresse de k8s-w1.lab>:30091/` répond **`accueil`** aussi.

## Les repères utiles

Un Service n'est qu'un sélecteur et des ports. Un Service sans endpoint, c'est
un sélecteur qui ne correspond aux labels d'aucun Pod. Des endpoints mais rien
qui répond, c'est souvent le port vers lequel il envoie.

Un Service NodePort a **trois** ports : celui du Service dans le cluster, celui
du conteneur vers lequel il envoie, et celui qu'il ouvre sur **chaque nœud**.
Sans valeur déclarée, Kubernetes tire ce dernier au hasard dans sa plage.

L'adresse de chaque nœud se lit dans la colonne `INTERNAL-IP` de
`kubectl get nodes -o wide`.

## Comment vous saurez que c'est bon

Chaque test vérifie un des quatre états ci-dessus. Les deux derniers font une
vraie requête, l'un vers le control plane, l'autre vers le worker : un NodePort
s'ouvre sur tous les nœuds, où que tournent les Pods.

```bash
dsoxlab check ckad-service-nodeport-reparer
```
