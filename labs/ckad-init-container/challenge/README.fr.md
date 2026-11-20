# Challenge : Réparer le gardien d'une application

## 📍 La situation

Dans le namespace **`lab`**, le Pod **`facturation`** calcule les factures
avec les prix du service de tarifs. Ce service est exposé par le Service
**`tarifs-svc`**. Sans lui, la facturation sort des montants à zéro.

Un init container, **`attendre-tarifs`**, devait empêcher `facturation` de
démarrer tant que les tarifs ne répondent pas. Pourtant `facturation` tourne
déjà, alors que rien ne répond derrière `tarifs-svc`. Le gardien n'a rien
retenu.

## 🎯 Ce que vous devez obtenir

1. Un Pod **`facturation`** dans `lab`, dont l'init container
   **`attendre-tarifs`** attend une vraie réponse de `tarifs-svc`, puis un
   conteneur principal **`main`**, image
   `nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb`.
2. Tant que rien ne répond derrière `tarifs-svc`, `facturation` reste en
   **`Init`** : constatez-le.
3. Un Pod **`tarifs`** dans `lab`, même image nginx, que `tarifs-svc`
   sélectionne.
4. Une fois `tarifs` prêt, l'init container se termine et `facturation` passe
   en `Running` sans que vous ayez rien fait d'autre.

## 🧭 Les repères utiles

Commencez par lire ce que fait le gardien actuel et comment le Service est
déclaré : son sélecteur et son port. `kubectl describe` montre l'un et
l'autre.

On ne peut pas changer les init containers d'un Pod qui existe : il faut le
recréer.

Une attente bornée vaut mieux qu'une attente sans fin : un gardien qui
abandonne après un nombre d'essais met le Pod en erreur, ce qui se voit, et
Kubernetes le relance. Une boucle `until` avec `wget` fait un bon gardien,
dans l'image
`busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4`.

## ✅ Comment vous saurez que c'est bon

Les tests lisent la définition de `facturation`, interrogent `tarifs-svc`,
et comparent l'ordre de démarrage des deux Pods.

```bash
dsoxlab check ckad-init-container
```
