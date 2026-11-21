# Challenge : Ramener au dépôt Git les modifications faites en direct

## 📍 La situation

L'annuaire de l'entreprise tourne sur le cluster kubeadm, dans le namespace
**`annuaire`**. Ses manifestes vivent dans le dépôt git **`~/annuaire`**, qui
est la source de vérité : la ConfigMap `annuaire-config`, le Deployment
`annuaire-api` et son Service. Vous êtes sur le control plane, avec `kubectl`
configuré.

Cette nuit, pendant un incident, l'astreinte a modifié l'annuaire **en direct
sur le cluster**, sans passer par le dépôt. Personne n'a noté quoi. L'équipe a
tranché ce matin : elle **garde le nombre de réplicas** monté pendant
l'incident, et **rien d'autre**.

## 🎯 Ce que vous devez obtenir

1. `kubectl diff` appliqué au dépôt `~/annuaire` ne trouve **aucun écart**
   avec le cluster. **Exigence bloquante.**
2. Le nombre de réplicas monté pendant la nuit est **gardé dans le cluster**
   et **reporté dans le dépôt**, dans un commit. L'arbre de travail du dépôt
   est propre. **Exigence bloquante.**
3. Toutes les **autres** modifications faites en direct ont disparu.
4. Le Deployment et la ConfigMap sont les **objets d'origine** : modifiés,
   jamais supprimés ni recréés. **Exigence bloquante.**
5. Chaque réplica de l'annuaire tourne sur la **configuration du dépôt**.

## 🧭 Les repères utiles

Une modification faite en direct ne se voit pas toujours dans `kubectl diff`.

## ✅ Comment vous saurez que c'est bon

Les tests lisent le cluster et le dépôt git, rejouent `kubectl diff` sur le
dépôt, et lisent la configuration de chaque Pod. Le nombre de réplicas et les
valeurs modifiées sont tirés au sort à la préparation. Le seuil de réussite
est de 80 %, et les trois exigences bloquantes doivent être tenues.

```bash
dsoxlab check k8s-challenge-ramener-le-cluster-au-depot
```
