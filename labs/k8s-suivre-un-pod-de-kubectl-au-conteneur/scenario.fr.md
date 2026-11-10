# Suivre un Pod de kubectl au conteneur

## La situation

Le cluster kind **`architecture`** fait tourner un control plane et trois
workers. Votre `kubectl` le vise déjà. Le namespace **`suivre-un-pod`** est
vide, et le relevé **`~/suivre-un-pod/etapes.txt`** attend vos réponses :
complétez la valeur après chaque deux-points.

## Ce que vous devez obtenir

1. Un Deployment **`suivi`** dans le namespace `suivre-un-pod`, avec **un
   réplica disponible**, sur cette image :

   ```text
   nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
   ```

2. **`scheduled`** nomme le composant qui a placé le Pod sur un Node.

3. **`pulled`**, **`created`** et **`started`** nomment le composant qui a
   tiré l'image, créé le conteneur et l'a démarré.

4. **`noeud-du-kubelet`** nomme le Node dont le kubelet a fait ce travail.

## Les repères utiles

Une fois le Deployment créé, l'API server n'a fait qu'enregistrer un souhait.
Chaque étape qui suit laisse un **événement** sur le Pod, et chaque événement
dit quel composant l'a écrit : `kubectl describe pod` les liste en bas, dans
l'ordre où ils se sont produits, avec une colonne **From**.
`kubectl get events -o wide` montre les mêmes événements pour tout le
namespace, avec une colonne SOURCE.

La raison de l'événement donne l'étape (`Scheduled`, `Pulled`, `Created`,
`Started`) ; le message de l'événement `Scheduled` nomme le Node choisi.

Les événements sont conservés **24 heures** sur ce cluster (une heure par
défaut dans Kubernetes). Après une pause plus longue, ceux du lab ont disparu :
`dsoxlab reset k8s-suivre-un-pod-de-kubectl-au-conteneur` repose la situation.

## Comment vous saurez que c'est bon

Les tests lisent votre Deployment et votre relevé, et confrontent le relevé au
Node qui fait réellement tourner le Pod.

```bash
dsoxlab check k8s-suivre-un-pod-de-kubectl-au-conteneur
```
