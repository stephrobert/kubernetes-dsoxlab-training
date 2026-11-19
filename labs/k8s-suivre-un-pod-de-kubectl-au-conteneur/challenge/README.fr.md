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

2. Après **`scheduled`** : le composant qui a placé le Pod sur un nœud.

3. Après **`pulled`**, **`created`** et **`started`** : le composant qui a
   téléchargé l'image, créé le conteneur et l'a démarré.

4. Après **`noeud-du-kubelet`** : le nœud dont le kubelet a fait ce travail.

## 🧭 Les repères utiles

Chaque étape du trajet laisse un **événement** sur le Pod, et chaque événement
dit quel composant l'a écrit. `kubectl describe pod` les liste à la fin, dans
l'ordre, avec une colonne `From`. `kubectl get events -o wide` montre les mêmes
événements pour tout le namespace, avec une colonne `SOURCE`.

La raison de l'événement donne l'étape (`Scheduled`, `Pulled`, `Created`,
`Started`). Le message de l'événement `Scheduled` donne le nœud choisi.

Sur ce cluster, les événements sont gardés **24 heures** (une heure par défaut
dans Kubernetes). Après une longue pause, ceux du lab ont disparu : relancez
alors `dsoxlab reset k8s-suivre-un-pod-de-kubectl-au-conteneur`.

## ✅ Comment vous saurez que c'est bon

Les tests lisent votre Deployment et votre fichier. Ils comparent vos réponses
au nœud qui fait vraiment tourner le Pod.

```bash
dsoxlab check k8s-suivre-un-pod-de-kubectl-au-conteneur
```
