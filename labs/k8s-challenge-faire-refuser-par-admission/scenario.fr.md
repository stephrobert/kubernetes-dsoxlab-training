# Imposer une règle d'admission et prouver le refus, sans guidage

## La situation

Le cluster kubeadm admet tout. L'équipe sécurité veut qu'il **refuse** ce qui
enfreint ses règles, dès la création, plutôt que de compter sur la discipline
de chacun. Le setup a préparé quatre namespaces :

- **`vitrine`** n'applique aucun standard de sécurité. Un Pod de vitrine nommé
  **`catalogue`** doit y tourner, `busybox:1.37` qui exécute `sleep`.
- **`paiement`** fait tourner **`caisse`**, un Pod que personne n'a signalé et
  qui cumule les défauts. Il faut le reconstruire proprement sous le nom
  **`caisse-durcie`**, pour qu'il fasse la même chose.
- **`production`** accepte n'importe quelle image, y compris désignée par un
  simple tag. Un Pod **`conforme`** y tourne déjà, épinglé par son digest :
  n'y touchez pas.
- **`recette`** est un namespace de test. Rien n'y est demandé, et rien ne
  doit y changer.

Vous êtes sur le plan de contrôle, avec `kubectl` configuré. Aucune procédure
n'est donnée : le module vous a appris ce qu'il faut.

## Ce que vous devez obtenir

1. **`vitrine`** déclare le standard **restricted** dans les trois modes :
   **enforce**, **warn** et **audit**.
2. Le Pod **`catalogue`** **tourne** dans `vitrine`.
3. `catalogue` satisfait les **quatre exigences** du standard : il tourne en
   **non root**, ne peut pas **élever ses privilèges**, a **retiré ses
   capabilities**, et déclare un **profil seccomp**.
4. L'admission de `vitrine` **refuse** un Pod qui viole le standard et
   **accepte** un Pod conforme.
5. **`caisse-durcie`** **tourne** dans `paiement`.
6. `caisse-durcie` ne conserve **aucun des défauts** que vous relevez dans
   `caisse`.
7. Le Pod d'origine **`caisse`** **n'existe plus**.
8. Le conteneur de `caisse-durcie` **ne voit plus les processus de l'hôte** et
   ne tourne pas en root.
9. Une politique d'admission **native**, évaluée par l'API server lui-même, est
   liée en mode **refus**, et pas seulement en avertissement.
10. Dans **`production`**, un Pod dont l'image est désignée par un **tag** est
    **refusé**, un Pod dont l'image est **épinglée par son digest** est
    **accepté**, et les **autres namespaces**, `recette` en tête, ne sont **pas
    touchés**.

## Comment vous serez noté

Dix états, à poids égal. Le seuil est de **70 sur 100**, et les états **4 et
10** sont **bloquants** : les deux refus prouvés par de vraies soumissions.
Réussir les autres ne compense pas l'un d'eux manqué.

Les tests lisent les Pods admis, entrent dans le nouveau Pod pour compter ce
qu'il voit, et soumettent de vrais Pods : dans `vitrine` sans rien créer, dans
`production` et `recette` en les créant puis en les retirant aussitôt. Le
retour se limite au verdict : réussi ou non, et la note.

```bash
dsoxlab check  k8s-challenge-faire-refuser-par-admission
dsoxlab submit k8s-challenge-faire-refuser-par-admission
```
