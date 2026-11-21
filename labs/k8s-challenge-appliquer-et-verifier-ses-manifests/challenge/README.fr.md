# Challenge : Appliquer et vérifier ses manifests, d'après un cahier des charges

## 📍 La situation

L'équipe annuaire vous confie la livraison de son application sur le cluster
kind `lab`. Elle ne vous donne pas de manifests : seulement son cahier des
charges, dans **`~/annuaire/cahier-des-charges.txt`**. Il dit ce que
l'application doit faire, jamais quels objets écrire.

Elle veut deux variantes, **recette** et **production**, tirées d'une même
base, et une livraison qu'elle puisse rejouer sans surveiller l'écran.

## 🎯 Ce que vous devez obtenir

1. Une base Kustomize dans **`~/annuaire/base/`**, et deux variantes qui en
   partent : **`~/annuaire/recette/`** et **`~/annuaire/production/`**. Chaque
   variante crée son namespace. **Exigence bloquante.**

2. L'application **annuaire** tourne dans les deux variantes, telle que le
   cahier des charges la décrit.

3. Le délai que fixe le cahier des charges est posé sur le bon champ d'API,
   dans les deux variantes.

4. Les objets de production sont appliqués de façon **déclarative**.

5. La production passe ensuite à l'image
   `nginx:1.31.2@sha256:b5a9a3cfc86b81dd6f1458d53f2ad2b559cc255653d2efd6cacee5636bf2066f`,
   la recette reste en 1.30.5. **Avant** d'appliquer ce changement, vous
   enregistrez ce qu'il va modifier dans **`~/annuaire/diff-production.txt`**.

6. Un script **`~/annuaire/livrer.sh`** prend le nom d'une variante (`recette`
   ou `production`), l'applique de façon déclarative, et **ne rend la main
   qu'une fois l'application disponible**. **Exigence bloquante.**

## ✅ Comment vous saurez que c'est bon

Les tests construisent vos deux variantes, lisent le cluster, puis effacent le
namespace de production et lancent `livrer.sh production` : à son retour, les
trois exemplaires doivent déjà être disponibles. Le délai du cahier des charges
est tiré au sort à la préparation. Le seuil de réussite est de 70 %, et les
deux exigences bloquantes doivent être tenues.

```bash
dsoxlab check k8s-challenge-appliquer-et-verifier-ses-manifests
```
