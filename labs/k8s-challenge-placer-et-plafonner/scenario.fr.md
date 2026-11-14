# Placer des Pods, plafonner un namespace et dimensionner, sans guidage

## La situation

Sur le cluster kind **`capacite`** que votre `kubectl` vise déjà (un control
plane, trois workers), le namespace **`atelier`** fait tourner quatre
applications, déployées sans aucune règle de placement ni ressource :

- **`rendu`**, le moteur de rendu, qui doit avoir un nœud pour lui seul ;
- **`accueil`**, la page d'accueil ordinaire, qui doit suivre sa charge ;
- **`stockage`**, qui a besoin d'un disque rapide ;
- **`galerie`**, deux réplicas qui doivent survivre à la perte d'un nœud.

Le namespace n'a aucun plafond et ne donne aucune valeur par défaut à ses
conteneurs. Un metrics-server répond : `kubectl top pods` fonctionne.

Aucune procédure n'est donnée : le module vous a appris ce qu'il faut.

## Ce que vous devez obtenir

1. Le nœud **`capacite-worker3`** est réservé : il porte le taint
   **`dedie=calcul:NoSchedule`** et le label **`dedie=calcul`**.
2. **`rendu`** tourne sur `capacite-worker3`, parce qu'il **tolère** le taint
   **et** **sélectionne** ce nœud. **`accueil`** tourne **ailleurs**.
3. **`stockage`** demande une affinité de nœud **obligatoire** sur
   **`disque=ssd`** et une **préférée**, de poids **50**, pour la zone
   **`zone-b`** (`topology.kubernetes.io/zone`). Le nœud **`capacite-worker2`**
   porte le label **`disque=ssd`**, et `stockage` y tourne.
4. Les réplicas de **`galerie`** tournent sur des **nœuds différents**, et sa
   description le garantit.
5. Un **ResourceQuota** plafonne `atelier` à **2 CPU** et **2Gi** de requests,
   **4 CPU** et **4Gi** de limits, et **15 Pods**. Un Pod qui demande plus est
   refusé, ce que montre un dry-run côté serveur.
6. Un **LimitRange** donne à tout conteneur qui ne déclare rien une demande de
   **100m** de CPU et **128Mi**, et une limite de **200m** de CPU et
   **256Mi** : un Pod sans requests est accepté, et revient complété.
7. Un **HPA** met **`accueil`** à l'échelle entre **2** et **5** réplicas, à
   **50 %** d'utilisation CPU moyenne, et il **lit une valeur** : sa cible
   n'est pas `<unknown>`.
8. **Sous charge**, le HPA porte `accueil` **au-delà de son minimum**.

## Comment vous serez noté

Huit états, à poids égal. Le seuil est de **70 sur 100**, et les états **2
et 5** sont **bloquants** : l'application réservée sur son nœud, et le
plafond du namespace. Réussir les autres ne compense pas l'échec de l'un
d'eux.

Les tests lisent où les Pods tournent vraiment et ce que demandent leurs
descriptions, et soumettent des Pods d'essai en dry-run côté serveur, qui ne
crée rien. Pour l'état 8, **le test génère lui-même la charge** : il fait
tourner une boucle de calcul dans chaque Pod d'`accueil` pendant environ deux
minutes, et attend au plus deux minutes que le Deployment grossisse. Vous
n'avez rien à lancer pour cela, et une vérification peut durer ce temps-là.

Quatre **indices** sont proposés, et chacun retire des points au barème avant
le calcul de la note : 2, 3, 5 puis 5. Le retour se limite au verdict : réussi
ou non, et la note.

```bash
dsoxlab check  k8s-challenge-placer-et-plafonner
dsoxlab submit k8s-challenge-placer-et-plafonner
```
