# Ne laisser entrer que des images vérifiées, sans guidage

## La situation

L'équipe de livraison veut que le cluster kubeadm ne fasse tourner que des
images **épinglées**, **analysées** et **signées**. Aujourd'hui, rien de tout
cela n'est vrai. Dans le namespace **`livraison`** :

- le Deployment **`vitrine`** fait tourner `nginx:1.27-alpine`, désignée par son
  tag ;
- le Deployment **`boutique`** fait tourner `nginx:1.21`, une image de 2021 ;
- un **registre local** répond en `localhost:5000` sur le plan de contrôle. Il
  porte `localhost:5000/appli/web:1.0`, l'image que l'équipe veut livrer, et
  `localhost:5000/appli/outil:1.0`, une autre image. **Aucune n'est signée.**

Sur le nœud, l'application **`inventaire`** a son Dockerfile dans
`/root/inventaire/`. Il construit et tourne, et une analyse statique le
rejette.

`cosign`, `crane` et `trivy` sont posés sur le nœud. **Kyverno 1.19.2** est
installé dans le cluster, **sans aucune politique** : il joint le registre
local à la même adresse, `localhost:5000`.

Vous êtes sur le plan de contrôle, avec `kubectl` et `sudo`. Aucune procédure
n'est donnée : le module vous a appris ce qu'il faut.

## Ce que vous devez obtenir

1. **`vitrine`** référence son image par son **digest**, et non par un tag.
2. C'est toujours l'image demandée, **`nginx:1.27-alpine`**, et pas une autre
   version.
3. Le digest déclaré est celui que le **nœud exécute**, et les deux réplicas
   tournent.
4. Les **constats de l'analyse statique** du Dockerfile ont disparu, et l'image
   **fait toujours la même chose** : une image Node qui lance `server.js`.
5. Une **clé publique** est publiée dans le cluster, dans un ConfigMap nommé
   **`cosign-pub-key`** dans `livraison`, sous la clé **`cosign.pub`**. La clé
   privée reste sur le nœud.
6. La **signature** de `appli/web:1.0` est **poussée** dans le registre, à côté
   de l'image.
7. La clé publiée **accepte** l'image signée et **refuse** l'autre.
8. **`boutique`** ne tourne plus sur son image d'origine, et fait toujours
   tourner nginx.
9. La nouvelle image porte **strictement moins de failles critiques** que
   l'ancienne, mesuré par un **nouveau scan**.
10. Le cluster **refuse à la création** un Pod dont l'image du registre local
    **n'est pas signée**, et **accepte** l'image signée.

## Comment vous serez noté

Dix états, à poids égal. Le seuil est de **70 sur 100**, et les états **3, 9
et 10** sont **bloquants** : une image vraiment épinglée, une image vraiment
moins exposée, et un cluster qui n'admet que du signé. Réussir les autres ne
compense pas l'un d'eux manqué.

Les tests demandent au runtime du nœud ce qui tourne, relancent l'analyse
statique et les scans de vulnérabilités, vérifient les signatures avec la clé
prise dans le ConfigMap, puis soumettent deux Pods à l'admission sans les
créer. Le retour se limite au verdict : réussi ou non, et la note.

```bash
dsoxlab check  k8s-challenge-livrer-une-image-verifiee
dsoxlab submit k8s-challenge-livrer-une-image-verifiee
```
