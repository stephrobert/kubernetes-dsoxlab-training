# Exiger le mTLS dans un maillage, et le prouver par un client qui reste dehors

## La situation

Une application tourne dans un maillage de services Istio. Chacun de ses Pods
porte un sidecar, et le trafic entre eux **peut** être chiffré.

Peut, seulement. L'audit vient de le montrer : un Pod quelconque du cluster,
qui n'appartient pas au maillage et ne présente donc aucun certificat de
charge de travail, joint le service sans difficulté et lit sa réponse en
clair. Le maillage a été posé, mais rien ne lui a été **exigé**.

Vous disposez de trois Pods. Dans le namespace **`maillage`**, qui reçoit les
sidecars : **`service`**, qui sert une page, et **`client-maille`**, qui
l'appelle. Dans le namespace **`dehors`**, sans sidecar : **`client-nu`**.

## Ce que vous devez obtenir

1. Le namespace `maillage` n'accepte plus que du trafic mutuellement
   authentifié, quelle qu'en soit la provenance.

2. `client-nu`, depuis `dehors`, **ne joint plus** `service`.

3. `client-maille` **joint toujours** `service`. L'application ne doit pas
   tomber : ce n'est pas une coupure que l'on vous demande, c'est une
   exigence.

N'installez ni ne désinstallez rien : le maillage est déjà là.

## Les repères utiles

Ce qui règle ce qu'un Pod du maillage accepte en **entrée** est un objet
Istio, pas un objet Kubernetes natif : ni NetworkPolicy, ni Ingress.

Cet objet a un **mode**. Celui qui est en vigueur par défaut accepte le
chiffré comme le clair, et existe pour migrer une application sans la couper.
Un autre n'accepte que le TLS mutuel.

Il se pose dans le namespace du service **appelé**, pas dans celui de
l'appelant.

Sans champ `selector`, il vaut pour tout le namespace ; avec un `selector`, il
ne vaut que pour les Pods qu'il désigne.

La règle descend jusqu'aux sidecars par istiod. Elle n'agit pas à la seconde
où l'API accepte l'objet : laissez-lui quelques secondes.

## Comment vous saurez que c'est bon

Le dernier test exerce **les deux côtés** : il attend que `client-nu` soit
bloqué, puis vérifie que `client-maille` passe encore. Un objet posé en mode
permissif laisserait les deux passer ; une exigence mal placée les bloquerait
tous les deux. Ni l'un ni l'autre ne compte comme une réussite.

```bash
dsoxlab check cks-istio-mtls-lockdown
```
