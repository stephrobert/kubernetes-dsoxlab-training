# Challenge : Inspecter une release Helm en échec et la restaurer

## 📍 La situation

Dans le namespace **`helm-demo`**, la release **`vitrine`** déploie le chart
**podinfo**. Elle a connu plusieurs montées de version, et les dernières ont
échoué. Le dépôt de charts `podinfo` est déjà déclaré pour vous (`helm repo
list`).

Vous êtes sur le control plane, avec `kubectl` et `helm` 4.3.2. Vos réponses
s'écrivent dans **`~/vitrine`**.

## 🎯 Ce que vous devez obtenir

1. **`~/vitrine/derniere-version.txt`** contient, sur une ligne, la **dernière
   version de la série 6.14** du chart podinfo publiée dans le dépôt.
2. **`~/vitrine/revisions-en-echec.txt`** contient les **numéros de toutes
   les révisions** de `vitrine` qui ont échoué, séparés par des espaces.
3. La release est **revenue à la dernière révision saine** : sa dernière
   révision est un retour arrière déployé vers elle, et l'application est
   disponible.
4. Les **tests du chart** ont réussi sur la révision courante, déployée.

## 🧭 Les repères utiles

`helm search repo` cherche dans les dépôts déclarés, et rend par défaut la
dernière version de toutes. `helm status` et `helm get` décrivent une
release. `helm history` liste ses révisions, avec leur statut. Un retour
arrière ne supprime aucune révision : il en crée une nouvelle, copie de la
révision visée, et sans numéro il vise la révision précédente. `helm test`
lance les tests qu'un chart contient, et leur résultat reste attaché à la
révision.

## ✅ Comment vous saurez que c'est bon

Les tests relancent eux-mêmes `helm search repo` et `helm history`, les
comparent à vos fichiers, puis lisent l'historique et le statut de la release.

```bash
dsoxlab check k8s-inspecter-et-restaurer-une-release-helm
```
