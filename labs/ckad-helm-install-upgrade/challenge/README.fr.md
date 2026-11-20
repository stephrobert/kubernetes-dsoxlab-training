# Challenge : Installer, mettre à jour et revenir en arrière avec Helm 4

## 📍 La situation

L'équipe livre son application web sous forme de **chart Helm**, dans le
répertoire **`~/charts/web`** du control plane. Le chart est en version
**0.1.0** et déploie nginx 1.30.5. Helm 4 est installé. Le namespace **`lab`**
existe, et il est vide.

L'équipe prépare la version suivante du chart. Elle doit passer en
production, puis en être retirée si elle pose problème.

## 🎯 Ce que vous devez obtenir

1. Une release **`web`** dans `lab`, installée depuis `~/charts/web` en
   version **0.1.0**, avec les valeurs par défaut du chart.
2. Le chart passé en version **0.2.0**, et la release **mise à jour** avec
   cette version, **3** réplicas et un label de Pod **`tier=front`**.
3. La release **revenue à sa révision 1** : l'historique montre le chart
   `web-0.1.0`, puis `web-0.2.0`, puis le retour, qui ramène `web-0.1.0`.
4. L'application **tourne** avec un réplica et **répond** : le Deployment est
   prêt, et son Service sert la page nginx.

## 🧭 Les repères utiles

La version d'un chart est le champ `version` de son `Chart.yaml`. Helm
l'enregistre dans chaque révision : c'est la colonne `CHART` de
`helm history`.

Le `values.yaml` du chart dit le nom des valeurs qu'il accepte, dont le
nombre de réplicas et les labels ajoutés aux Pods.

## ✅ Comment vous saurez que c'est bon

Les tests lisent l'historique de la release, les valeurs de chaque révision,
l'état du Deployment et l'image que le chart rend, puis interrogent le
Service.

```bash
dsoxlab check ckad-helm-install-upgrade
```
