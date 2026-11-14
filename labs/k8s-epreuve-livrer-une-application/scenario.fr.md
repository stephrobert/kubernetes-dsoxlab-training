# Épreuve du niveau 3 : exposer, configurer et livrer une application

## La situation

Un festival de musique vous confie sa plateforme, sur le cluster kind
**`capacite`** que votre `kubectl` vise déjà : un control plane et trois
workers. L'équipe précédente est partie dans la précipitation. Le cahier des
charges dit ce qu'il faut obtenir, pas comment : c'est à vous de choisir les
ressources, et de trouver ce qui est cassé.

Ce dont vous héritez :

- l'espace **`festival`** contient la billetterie **`billets`** (le frontend,
  deux exemplaires), l'application **`programme`**, la base de données
  **`registre`** et un générateur d'affiches **`affiches`**. Plusieurs ne
  tournent pas, ou pas comme il faut ;
- l'espace **`paiement`** contient le composant de paiement **`caisse`**, qui
  ne répond plus à **`http://caisse.paiement`**, alors que ses exemplaires
  tournent ;
- l'espace **`partenaires`** contient **`partenaire`**, le client d'un
  partenaire ;
- le nœud **`capacite-worker3`** est réservé à la base : l'équipe plateforme
  l'a fermé aux autres charges et l'a étiqueté **`reserve=registre`**.

Le point d'entrée HTTP du cluster, Traefik, répond sur le port **30080** de
chaque nœud, à l'adresse du nœud. Il sert les routes HTTP standard du cluster.

## Le cahier des charges

1. **Exposition.** De l'extérieur du cluster, pour l'hôte
   **`festival.local`**, le chemin **`/billets`** atteint la billetterie et le
   chemin **`/programme`** atteint le programme. Un chemin non déclaré, ou un
   autre hôte, n'atteint ni l'une ni l'autre.
2. **Le composant en panne.** Avant toute réparation, écrivez dans
   **`~/epreuve/cause-caisse.txt`** pourquoi `caisse` ne répond pas : nommez
   ce qui l'en empêche, et comment. Réparez ensuite, sans plus toucher au
   fichier : sa date est comparée à celle de votre réparation. `caisse`
   répond de nouveau à `http://caisse.paiement` depuis n'importe quel Pod du
   cluster.
3. **Résolution de noms.** Depuis `partenaire`, le nom complet
   **`programme.festival.svc.cluster.local`** se résout, et le programme y
   répond en HTTP, sur le port **80**.
4. **Isolement.** Sur le port **5432** de la base, seule la billetterie
   entre. Le programme est refusé, comme tout client d'un autre espace.
5. **La sortie de la base.** La base résout toujours les noms, et toute
   autre sortie lui est refusée.
6. **Placement.** La base tourne sur le nœud réservé, et rien d'autre de
   `festival` n'y tourne. Les deux exemplaires de la billetterie ne partagent
   jamais un nœud : leur description le garantit, ce n'est pas laissé au
   hasard.
7. **Le plafond.** `festival` dans son ensemble ne réserve jamais plus de
   **2 CPU** et **2 Gio** de mémoire, ne dépasse jamais **4 CPU** et
   **4 Gio** en limites, et ne compte pas plus de **15 Pods**. Une charge qui
   le dépasserait est refusée à la création.
8. **Valeurs par défaut.** Un conteneur de `festival` qui ne déclare rien
   reçoit une demande de **100m** de CPU et **128Mi** de mémoire, et une
   limite de **250m** de CPU et **256Mi**. La charge `affiches` tourne.
9. **Mise à l'échelle.** Le programme suit sa charge processeur entre **2**
   et **6** exemplaires, en visant **60 %** du CPU que réserve chaque
   exemplaire, et sa mise à l'échelle lit vraiment une valeur.
10. **Identité.** Le programme tourne sous une identité qui lui est propre,
    qu'aucune autre charge n'utilise. Il n'appelle jamais l'API : aucun
    identifiant n'est remis à ses conteneurs. Cette identité peut **lire les
    ConfigMaps de `festival`**, et rien d'autre, nulle part : aucun autre
    droit dans l'espace, aucun ailleurs, aucun sur le cluster.
11. **Durcissement.** Le conteneur du programme tourne **sans root**, sous
    un utilisateur numérique, avec une **racine en lecture seule** et **sans
    aucune capacité**, et le programme répond toujours.

## Comment vous serez noté

L'épreuve est notée sur **l'état final du cluster** et sur le fichier de
cause, jamais sur les commandes tapées. Elle compte **onze critères**, un par
exigence, tous de même poids. Le seuil est de **70 sur 100**, soit huit
critères au moins, et **six critères sont critiques** : ils doivent tous
réussir, quel que soit le total. Ce sont l'exposition (1), le composant réparé
après consignation de sa cause (2), l'isolement de la base (4), le plafond
(7), l'identité (10) et le durcissement (11).

Chaque vérification agit sur le cluster : elle lance des commandes dans
`partenaire` et dans des exemplaires de vos applications, et soumet des
charges d'essai à `festival` en dry run côté serveur, qui ne crée rien.

Aucune procédure n'est donnée, et l'épreuve n'offre **aucun indice** : les
leçons du niveau 3 ont tout enseigné. Comptez environ deux heures.

```bash
dsoxlab check  k8s-epreuve-livrer-une-application
dsoxlab submit k8s-epreuve-livrer-une-application
```
