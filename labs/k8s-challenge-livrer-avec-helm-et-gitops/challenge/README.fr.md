# Challenge : Livrer une application avec Helm et GitOps, depuis une image construite

## 📍 La situation

L'équipe boutique vous confie deux livraisons sur le cluster kind `lab`.

La première est la **vitrine**. Son code est dans **`~/livraison/app`**, avec
son Dockerfile, et son chart Helm dans **`~/livraison/chart-vitrine`**. Lisez le
`values.yaml` du chart : il dit tout ce qui se règle.

La seconde est le **catalogue**. Ses manifests vivent dans un dépôt Git, et
l'équipe veut que le cluster suive ce dépôt tout seul. Argo CD est installé dans
le namespace `argocd`, et il a déjà les accès au dépôt. Votre clone de travail
est dans **`~/livraison/catalogue`**.

Ce que l'environnement fournit :

- un **registre d'images** dans le cluster, le Service `registre` du namespace
  `registre`. Le cluster tire ses images en **`localhost:30500`**. Depuis la
  VM, on y pousse en ouvrant d'abord un tunnel :
  `kubectl -n registre port-forward svc/registre 30500:5000` ;
- le **dépôt Git** du catalogue, que le cluster joint à l'adresse
  **`ssh://git@172.18.0.1/srv/git/catalogue.git`** ;
- `docker`, `helm` et `kubectl` sur la VM. Argo CD n'y a pas de CLI :
  `kubectl` suffit pour le piloter.

## 🎯 Ce que vous devez obtenir

1. L'image de la vitrine est construite depuis `~/livraison/app` et poussée
   dans le registre sous le nom **`localhost:30500/vitrine:1.0`**.

2. La release Helm **`vitrine`** du chart `~/livraison/chart-vitrine` est
   installée dans le namespace **`vitrine`**, depuis un fichier de values que
   vous écrivez en **`~/livraison/values-vitrine.yaml`**. Ce fichier demande
   **2 exemplaires** et l'image que vous avez construite. Il reste tel qu'il a
   servi à l'installation.

3. La vitrine tourne sur l'image construite, **épinglée par son digest**, et
   ses deux exemplaires sont prêts. **Exigence bloquante.**

4. La release est ensuite **mise à jour à 3 exemplaires** (révision 2), puis
   **ramenée à la révision 1**.

5. Une Application Argo CD **`catalogue`**, dans le namespace `argocd`, suit
   le dépôt du catalogue (dossier **`catalogue`**) et déploie dans le
   namespace **`catalogue`**, en **synchronisation automatique**. Elle est
   **Synced** et **Healthy** sur le **dernier commit** du dépôt.
   **Exigence bloquante.**

6. Le catalogue passe à **2 exemplaires**, par un commit **poussé** dans le
   dépôt, jamais par une commande sur le cluster. Argo CD l'a appliqué. Il
   relit le dépôt toutes les trois minutes environ.

## ✅ Comment vous saurez que c'est bon

Les tests interrogent le registre et la page servie par la vitrine,
relisent l'historique de la release et ses values révision par révision,
lisent l'état de l'Application Argo CD et le comparent au dernier commit du
dépôt. Le contenu de `~/livraison/app` porte une marque tirée au sort à la
préparation : l'image qui tourne doit en venir.

Six exigences, à poids égal. Le seuil de réussite est de 70 %, et les deux
exigences bloquantes doivent être tenues. Le retour se limite à la liste des
critères non satisfaits et à la note.

```bash
dsoxlab check k8s-challenge-livrer-avec-helm-et-gitops
```
