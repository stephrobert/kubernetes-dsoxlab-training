# Revenir en arrière sur un déploiement bloqué, puis livrer la bonne version

## La situation

Dans le namespace **`lab`**, le Deployment **`webapp`** tourne en trois
replicas. Un collègue a lancé la mise à jour vers la nouvelle image ce
matin, avec une faute de frappe dans son nom. Depuis, `kubectl rollout
status` ne rend pas la main : un Pod neuf n'arrive pas à tirer son image,
les trois anciens tiennent le service, et le Deployment n'avance plus.

L'image attendue est **`nginx:1.27-alpine`**. C'est son tag qui compte : un
digest ajouté à ce tag est accepté, un autre tag ne l'est pas.

Vous êtes sur le control plane, avec `kubectl` configuré.

## Ce que vous devez obtenir

1. **D'abord**, la version qui marchait, celle d'avant la mise à jour,
   remise en service : `nginx:1.26-alpine`, en **révision 3** du Deployment.
   Le déploiement bloqué doit être quitté avant de livrer quoi que ce soit
   d'autre.

2. **Ensuite**, la bonne image livrée : `webapp` en `nginx:1.27-alpine`, en
   **révision 4** du Deployment, trois replicas demandés, trois replicas
   disponibles et à jour, et aucun Pod resté en erreur d'image.

3. Le Deployment porte une **cause de changement** : l'annotation
   `kubernetes.io/change-cause` sur le **Deployment lui-même**, avec un
   texte qui dit ce qui a été livré. C'est là que les tests la lisent.

4. L'historique est intact. Le ReplicaSet de la version qui marchait et
   celui de l'image fautive sont tous les deux encore là, et le fautif, qui
   reste en **révision 2**, est réduit à **zéro** : rien n'a été supprimé à
   la main, et le Deployment n'a été ni supprimé ni recréé.

Soit, à la fin, quatre révisions : la 1 de l'application d'origine, la 2 de
la mise à jour fautive de ce matin à zéro, la 3 de la version qui marchait
remise en service à zéro, la 4 de la bonne image avec ses trois replicas.

## Les repères utiles

Un Deployment garde ses anciens ReplicaSets, à zéro, et numérote chaque
changement de template. Revenir à la révision précédente ne détruit rien :
l'ancien ReplicaSet est réactivé et reçoit un nouveau numéro de révision.

`kubectl rollout history`, `kubectl rollout undo` et `kubectl set image`
sont les trois gestes, et `rollout undo` est celui que l'examen attend pour
l'étape 1 ; `kubectl describe deployment` dit pourquoi le déploiement est
bloqué, et `kubectl get pods` montre le Pod qui n'a pas d'image. Le
conteneur du template s'appelle `nginx`.

## Comment vous saurez que c'est bon

Les tests lisent le cluster réel : le Deployment, les Pods et les
ReplicaSets qui lui **appartiennent**, avec leurs annotations de révision.
Ils jugent l'état atteint, pas les commandes tapées, et ils ne savent pas
distinguer un `rollout undo` d'un `set image` vers l'image précédente : les
deux laissent le même historique.

```bash
dsoxlab check cka-deployment-rollout-rollback
```
