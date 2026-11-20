# Challenge : Revenir en arrière sur un déploiement bloqué, puis livrer la bonne version

## 📍 La situation

Vous êtes sur le control plane du cluster kubeadm, et votre kubectl est
configuré. Dans le namespace **`lab`**, le Deployment **`catalogue`** tourne avec
trois Pods, en `nginx:1.30.5-alpine`.

Ce matin, un collègue a voulu le mettre à jour, mais il s'est trompé d'image :
il a livré `busybox:1.38.0` à la place de nginx. Depuis, la mise à jour est
bloquée :

- un Pod neuf démarre, puis s'arrête, encore et encore ;
- les trois anciens Pods tiennent toujours le service ;
- `kubectl rollout status` ne rend pas la main.

L'image attendue est **`nginx:1.30.6-alpine`**. C'est son tag qui compte : vous
pouvez ajouter un digest à ce tag, mais pas choisir un autre tag.

## 🎯 Ce que vous devez obtenir

1. **D'abord**, remettez en service la version qui marchait,
   `nginx:1.30.5-alpine`.
   Elle doit devenir la **révision 3** du Deployment. Quittez la mise à jour
   bloquée avant de livrer quoi que ce soit d'autre.

2. **Ensuite**, livrez la bonne image : `catalogue` en `nginx:1.30.6-alpine`, en
   **révision 4**, avec trois Pods demandés, trois Pods disponibles et à jour,
   et plus aucun Pod en panne.

3. Le Deployment `catalogue` porte une **cause de changement** : l'annotation
   `kubernetes.io/change-cause`, posée sur le Deployment lui-même, avec un
   texte qui dit ce qui a été livré.

4. L'historique est intact. Ne supprimez aucun ReplicaSet à la main, et ne
   supprimez pas le Deployment. À la fin, l'historique compte donc quatre
   révisions :

   - la 2, la mise à jour fautive de ce matin, gardée à zéro Pod ;
   - la 3, la version qui marchait remise en service, à zéro Pod ;
   - la 4, la bonne image, avec ses trois Pods.

   La révision 1 n'apparaît plus : quand vous revenez à la version qui
   marchait, son ReplicaSet reçoit le numéro 3.

## 🧭 Les repères utiles

Un Deployment garde ses anciens ReplicaSets, à zéro Pod, et donne un numéro à
chaque changement de ses Pods. Revenir en arrière ne détruit rien : l'ancien
ReplicaSet reprend du service et reçoit un nouveau numéro.

Trois commandes suffisent : `kubectl rollout history`, `kubectl rollout undo`
et `kubectl set image`. Le conteneur du Deployment s'appelle `nginx`.
`kubectl describe deployment` dit pourquoi la mise à jour est bloquée, et
`kubectl get pods` montre le Pod qui s'arrête en boucle.

La cause de changement reste sur le Deployment, et chaque nouvelle révision
la recopie. Un retour en arrière, lui, remet la cause de la révision choisie.
Posez donc la vôtre après la livraison finale.

## ✅ Comment vous saurez que c'est bon

Les tests lisent le cluster : le Deployment, ses Pods et ses ReplicaSets, avec
leurs numéros de révision. Ils jugent l'état obtenu, pas les commandes tapées.
Ils ne distinguent donc pas un `rollout undo` d'un `set image` vers l'ancienne
image : les deux laissent le même historique.

```bash
dsoxlab check cka-deployment-rollout-rollback
```
