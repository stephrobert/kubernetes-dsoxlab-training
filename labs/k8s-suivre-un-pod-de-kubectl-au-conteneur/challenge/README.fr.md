# Challenge : Suivre un Pod de kubectl au conteneur

## 📍 La situation

Le cluster kind **`architecture`** fait tourner un control plane et trois
workers. Votre kubectl le vise déjà. Le namespace **`suivre-un-pod`** est vide.
Le fichier **`~/suivre-un-pod/etapes.txt`** attend vos réponses : complétez la
valeur après chaque deux-points.

## 🎯 Ce que vous devez obtenir

1. Un Deployment **`suivi`**, dans le namespace `suivre-un-pod`, avec **un Pod
   disponible**, sur cette image :

   ```text
   nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
   ```

2. Après **`pod`** : le nom complet du Pod que le Deployment a créé.

3. Après **`noeud-du-kubelet`** : le nœud choisi par le Scheduler, dont le
   kubelet a démarré le conteneur.

4. Après **`conteneur`** : l'identifiant que containerd a donné au conteneur
   du Pod.

## 🧭 Les repères utiles

Chaque étape du trajet laisse un **événement** sur le Pod, et chaque événement
dit quel composant l'a écrit. `kubectl describe pod` les liste à la fin, dans
l'ordre, avec une colonne `From`. `kubectl get events -o wide` montre les mêmes
événements pour tout le namespace, avec une colonne `SOURCE`.

La raison de l'événement donne l'étape (`Scheduled`, `Pulled`, `Created`,
`Started`). Le message de l'événement `Scheduled` donne le nœud choisi. Le
kubelet de ce nœud demande ensuite le conteneur à containerd :
`kubectl describe pod` affiche l'identifiant reçu sur la ligne `Container ID`.

Sur ce cluster, les événements sont gardés **24 heures** (une heure par défaut
dans Kubernetes). Après une longue pause, ceux du lab ont disparu : relancez
alors `dsoxlab reset k8s-suivre-un-pod-de-kubectl-au-conteneur`.

## ✅ Comment vous saurez que c'est bon

Les tests lisent votre Deployment et votre fichier. Ils comparent vos réponses
au Pod, au nœud et au conteneur qui tournent vraiment.

```bash
dsoxlab check k8s-suivre-un-pod-de-kubectl-au-conteneur
```
