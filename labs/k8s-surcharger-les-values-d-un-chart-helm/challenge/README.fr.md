# Challenge : Surcharger les values d'un chart Helm sans tomber dans le piège du type

## 📍 La situation

Dans le namespace **`helm-values`**, la release **`catalogue`** déploie le
chart **podinfo 6.16.0**. L'exploitation lui a donné deux réglages par
`--set` : **trois réplicas** et la couleur d'interface **`#ff6b00`**.

On vous demande de la monter en **6.17.0** et de fixer le message de
l'interface à **`2026`**, l'année du catalogue.

Vous êtes sur le control plane, avec `kubectl` et `helm` 4.3.2. Le dépôt
`podinfo` est déjà déclaré. Travaillez dans **`~/catalogue`** si vous écrivez
des fichiers de values.

## 🎯 Ce que vous devez obtenir

1. Les values de la release portent **`ui.message`** égal à la **chaîne**
   `"2026"`, et non à l'entier 2026.
2. La release est en **podinfo 6.17.0**, déployée, ses Pods font tourner
   l'image **6.17.0**, et elle garde les réglages de l'exploitation : **trois
   réplicas** et la couleur **`#ff6b00`**.
3. podinfo **répond** avec le message `2026`.

## 🧭 Les repères utiles

`helm get values` montre les values qu'une release a reçues. `--all` y ajoute
les défauts du chart. `-f` lit un fichier de values, `--set` pose une valeur à
la ligne de commande. `--set` devine le type : un nombre devient un entier, et
`true`, `false` et `null` deviennent des booléens ou rien. `--set-string`
garde une chaîne. Dès qu'un `helm upgrade` reçoit des values, il repart des
défauts du chart, plus ces seules values. `--reuse-values` reprend toutes
celles de la révision précédente, y compris les valeurs par défaut de
l'ancienne version du chart.

## ✅ Comment vous saurez que c'est bon

Les tests lisent les values et le statut de la release, puis interrogent
l'application.

```bash
dsoxlab check k8s-surcharger-les-values-d-un-chart-helm
```
