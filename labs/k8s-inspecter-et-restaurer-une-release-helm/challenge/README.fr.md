# Challenge : Inspecter une release Helm en échec et la restaurer

## 📍 La situation

Dans le namespace **`helm-demo`**, la release **`vitrine`** déploie le chart
**podinfo**. Elle tournait bien jusqu'à sa dernière montée de version, qui a
échoué. Le dépôt de charts `podinfo` est déjà déclaré pour vous (`helm repo
list`).

Vous êtes sur le control plane, avec `kubectl` et `helm` 4.3.2. Vos réponses
s'écrivent dans **`~/vitrine`**.

## 🎯 Ce que vous devez obtenir

1. **`~/vitrine/derniere-version.txt`** contient, sur une ligne, la **dernière
   version du chart podinfo** publiée dans le dépôt.
2. **`~/vitrine/revision-en-echec.txt`** contient le **numéro de la révision**
   de `vitrine` qui a échoué.
3. La release est **revenue à la dernière révision saine** : sa dernière
   révision est un retour arrière déployé, et l'application est disponible.
4. Les **tests du chart** ont réussi sur la révision courante.

## 🧭 Les repères utiles

`helm search repo` cherche dans les dépôts déclarés. `helm status` et
`helm get` décrivent une release. `helm history` liste ses révisions, avec leur
statut. Un retour arrière ne supprime aucune révision : il en crée une
nouvelle, copie de la révision visée. `helm test` lance les tests qu'un chart
contient, et leur résultat reste attaché à la révision.

## ✅ Comment vous saurez que c'est bon

Les tests relancent eux-mêmes `helm search repo` et `helm history`, les
comparent à vos fichiers, puis lisent l'historique et le statut de la release.

```bash
dsoxlab check k8s-inspecter-et-restaurer-une-release-helm
```
