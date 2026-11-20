# Challenge : Composer un Pod multi-conteneurs

## 📍 La situation

L'équipe photo veut publier sa vitrine sur le cluster kubeadm, dans le
namespace **`photo`**. La ConfigMap **`vitrine`** y porte, sous la clé
**`titre`**, le titre de l'exposition du moment. Rien d'autre n'existe. Vous
êtes sur le control plane, avec `kubectl` configuré.

Images à utiliser :

- serveur : `nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb` ;
- tâches auxiliaires : `busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4`.

## 🎯 Ce que vous devez obtenir

Un Deployment **`galerie`** à **deux** réplicas, dont chaque Pod réunit trois
conteneurs :

1. un init container **`generer-page`**, qui va jusqu'au bout avant le
   démarrage des autres et écrit la page d'accueil, contenant **le titre de la
   ConfigMap `vitrine`**, dans un volume **`page`**. Chaque Pod sert cette page
   sur son port 80. **Exigence bloquante.**
2. un sidecar natif **`relais-journaux`**, qui démarre avant le serveur, tourne
   à côté de lui et affiche dans **ses propres journaux** chaque accès que le
   serveur reçoit. **Exigence bloquante.**
3. le serveur **`serveur`**, qui monte le volume `page` **en lecture seule**.

Le journal d'accès du serveur passe par un volume **`journaux`** temporaire,
plafonné à **32Mi**, monté par le serveur et par le sidecar, et par eux seuls.

Les deux réplicas sont prêts, sans aucun redémarrage.

## 🧭 Les repères utiles

L'image nginx envoie par défaut son journal d'accès vers sa sortie standard,
pas vers un fichier.

## ✅ Comment vous saurez que c'est bon

Les tests lisent le Deployment et ses Pods, chargent la page de chaque Pod, et
envoient une requête vers un chemin tiré au sort, qui doit ressortir dans les
journaux du sidecar. Le titre est tiré au sort à la préparation. Le seuil de
réussite est de 80 %, et les deux exigences bloquantes doivent être tenues.

```bash
dsoxlab check k8s-challenge-composer-un-pod-multi-conteneurs
```
