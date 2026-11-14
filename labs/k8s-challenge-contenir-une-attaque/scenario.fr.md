# Détecter et contenir une persistance et un déni de service

## La situation

Deux incidents ont touché le cluster kubeadm le même matin.

Dans le namespace **`reservations`**, un attaquant est entré par un Pod nommé
**`diagnostic-reseau`**. Le compte sous lequel il tourne, **`maintenance`**, lit
les Secrets de tous les namespaces. L'équipe l'a retiré deux fois à la main : il
est revenu chaque fois en quelques secondes. À côté tourne l'application
légitime **`reservations`**, trois réplicas derrière son Service, que le métier
ne peut pas perdre.

Dans le namespace **`calcul-lots`**, la charge **`moulinette`** tourne deux
réplicas sans rien pour l'empêcher de prendre ce qu'elle veut. Elle est bornée
ici pour que le nœud reste sûr ; la prochaine ne le sera pas. L'équipe veut la
garder en marche, mais contenue.

Vous êtes sur le plan de contrôle, avec `kubectl` configuré, en root. Aucune
procédure n'est donnée : le module vous a appris ce qu'il faut.

## Ce que vous devez obtenir

1. Ce que l'attaquant a laissé pour garder son accès est **identifié** et
   consigné dans **`/root/constat-attaque.yaml`**, exporté de l'objet vivant,
   **avant toute suppression**.
2. Cet objet est **supprimé** et l'accès de l'attaquant **ne revient pas**, même
   une fois le Pod `diagnostic-reseau` supprimé : plus de compte `maintenance`,
   plus de jeton, plus aucun droit sur le cluster.
3. L'application légitime **`reservations`** a toujours ses **trois réplicas
   disponibles**.
4. **`calcul-lots`** plafonne ce qui est demandé : au plus **800m** de
   processeur et **768Mi** de mémoire, tous Pods confondus.
5. Un conteneur qui ne déclare aucune ressource dans `calcul-lots` reçoit des
   **requests et des limits par défaut**, en processeur et en mémoire.
6. Une **création au-delà de ce plafond** est refusée par le cluster.
7. Pendant que **`moulinette`** tourne toujours ses deux réplicas,
   **`reservations`** continue de répondre sur son Service.

## Comment vous serez noté

Sept états, à poids égal. Le seuil est de **70 sur 100**, et les états **2 et
6** sont **bloquants** : la persistance retirée pour de bon, et un plafond qui
refuse vraiment. Réussir les autres ne compense pas l'échec de l'un d'eux.

Les tests comparent le constat à l'objet posé par le setup, attendent un cycle
complet du mécanisme avant de juger que l'accès a disparu, créent des Pods
sondes dans `calcul-lots` pour voir ce que le cluster accepte et refuse, et
envoient de vraies requêtes HTTP à `reservations`. Le retour se limite à la
première ligne de chaque échec.

```bash
dsoxlab check  k8s-challenge-contenir-une-attaque
dsoxlab submit k8s-challenge-contenir-une-attaque
```
