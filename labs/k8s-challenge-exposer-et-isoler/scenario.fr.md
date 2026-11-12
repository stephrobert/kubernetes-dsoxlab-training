# Exposer une application et isoler ses flux

## La situation

Sur le cluster kubeadm du catalogue, l'équipe du **`comptoir`** a tout déployé
dans le namespace du même nom, mais rien n'est exposé ni protégé. Deux
applications, **`catalogue`** et **`panier`**, répondent chacune derrière son
Service. Un Service hérité, **`ancien`**, ne mène nulle part. Le Pod **`sonde`**
ne résout aucun nom. Et la base, le Pod **`base`**, accepte tout le monde, y
compris le Pod **`rodeur`** du namespace **`voisinage`**. Le cahier des charges
dit ce qu'il faut obtenir, pas comment.

Le cluster fournit un contrôleur Traefik, joignable sur le port **30080** du
nœud. Il sert les Ingress de classe **`traefik`** comme les Gateway de classe
**`traefik`**. Calico y applique les NetworkPolicies.

## Le cahier des charges

1. Pour l'hôte **`comptoir.local`**, le chemin **`/catalogue`** atteint
   l'application `catalogue` et le chemin **`/panier`** l'application `panier`.
   Un chemin non déclaré, ou un autre hôte, n'atteint ni l'une ni l'autre.
2. Cette route s'appelle **`vitrine`**. C'est un Ingress ou une HTTPRoute, au
   choix, et son contrôleur l'a **prise en charge** : l'Ingress porte une
   adresse, ou la Gateway de la HTTPRoute est programmée et l'a acceptée.
3. Le Service **`ancien`** a des endpoints : les Pods du Deployment `ancien`,
   joints sur le port où leur conteneur **écoute vraiment**.
4. Le Pod **`sonde`** résout le nom du Service `catalogue` par le **DNS du
   cluster**, et le joint en HTTP par son nom court.
5. Une NetworkPolicy **`base-refus-par-defaut`** pose un **refus par défaut**,
   en entrée comme en sortie, sur le Pod `base` et sur lui seul. Elle
   n'autorise rien elle-même.
6. Sur le port **5432** de la base, le Pod `backend` entre. Le Pod `frontend`
   est refusé, et `rodeur` aussi, bien qu'il porte le même label que `backend`.
7. La base **résout toujours des noms** malgré le refus par défaut, et ne joint
   rien d'autre.

## Comment vous serez noté

Le challenge est noté sur l'**état final** du cluster, jamais sur les commandes
tapées. Les **sept exigences pèsent toutes autant**. Le seuil est de **70 sur
100**, et **trois exigences sont bloquantes** : elles doivent réussir quel que
soit le total. Ce sont les chemins routés (exigence 1), la résolution de `sonde`
(exigence 4), et l'accès à la base réservé au backend (exigence 6).

Quatre **indices** sont proposés, et chacun retire des points du barème avant
le calcul de la note : 2, 3, 5 puis 5, soit 15 au plus. Sans indice, sept
exigences donnent 100, six en donnent 86 et cinq en donnent 71. Avec les quatre,
sept exigences donnent 85, six en donnent 73, et cinq ne suffisent plus : 61.

Aucune procédure n'est donnée : les leçons du module ont tout enseigné.

```bash
dsoxlab check  k8s-challenge-exposer-et-isoler
dsoxlab submit k8s-challenge-exposer-et-isoler
```
