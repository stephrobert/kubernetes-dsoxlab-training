# Revenir en arrière sur un déploiement bloqué, puis livrer la bonne version

## La situation

Dans le namespace **`lab`**, le Deployment **`webapp`** tourne en trois
replicas. Un collègue a lancé la mise à jour vers la nouvelle image ce
matin, avec une faute de frappe dans son nom. Depuis, `kubectl rollout
status` ne rend pas la main : un Pod neuf n'arrive pas à tirer son image,
les trois anciens tiennent le service, et le Deployment n'avance plus.

L'image attendue est **`nginx:1.27-alpine`**.

Vous êtes sur le control plane, avec `kubectl` configuré.

## Ce que vous devez obtenir

1. **D'abord**, le Deployment ramené à la révision qui marchait, celle
   d'avant la mise à jour, en passant par son historique. Le déploiement
   bloqué doit être défait avant de tenter autre chose.

2. **Ensuite**, la bonne image livrée : `webapp` en `nginx:1.27-alpine`,
   trois replicas disponibles, aucun Pod en erreur d'image.

3. La révision finale porte une **cause de changement** : l'annotation
   `kubernetes.io/change-cause` sur le Deployment, avec un texte qui dit ce
   qui a été livré.

4. Le ReplicaSet de l'image fautive est toujours là, réduit à **zéro**,
   comme l'historique le veut : rien n'a été supprimé à la main.

## Les repères utiles

Un Deployment garde ses anciens ReplicaSets, à zéro, et numérote chaque
changement de template. Revenir en arrière ne détruit rien : l'ancien
ReplicaSet est réactivé et reçoit un nouveau numéro de révision. C'est ce
numéro, sur chaque ReplicaSet, que les tests lisent pour savoir ce qui
s'est passé et dans quel ordre.

`kubectl rollout history`, `kubectl rollout undo` et `kubectl set image`
sont les trois gestes ; `kubectl describe deployment` dit pourquoi le
déploiement est bloqué, et `kubectl get pods` montre le Pod qui n'a pas
d'image.

## Comment vous saurez que c'est bon

Les tests lisent le Deployment, ses Pods et ses ReplicaSets avec leurs
annotations de révision.

```bash
dsoxlab check cka-deployment-rollout-rollback
```
