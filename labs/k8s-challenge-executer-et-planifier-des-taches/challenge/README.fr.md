# Challenge : Exécuter des tâches ponctuelles et planifiées

## 📍 La situation

Le service comptable confie trois traitements au cluster kubeadm, dans le
namespace **`compta`**. Vous êtes sur le control plane, avec `kubectl`
configuré.

- La ConfigMap **`lots`** liste les lots de factures du jour : une clé
  **`lot-<index>`** par lot, à partir de `lot-0`. Leur nombre change d'un jour
  à l'autre.
- La ConfigMap **`export-config`** porte la période à exporter.
- Le Job **`export-compta`** a échoué cette nuit.

Toutes les tâches utilisent l'image
`busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4`.

## 🎯 Ce que vous devez obtenir

1. Un Job **`facturer-lots`** qui traite **chaque lot une fois** : autant de
   complétions que de lots, chaque Pod prend le lot de **son propre numéro**
   et écrit dans ses journaux une ligne **`lot <index> : <nom du lot>`**. Le
   Job se termine avec succès. **Exigence bloquante.**
2. `facturer-lots` fait tourner **deux** Pods à la fois et n'accorde **qu'une**
   reprise.
3. Un CronJob **`relance-impayes`** s'exécute **du lundi au vendredi à
   6 h 15, heure de Paris**. Une exécution qui démarre remplace celle qui
   tournerait encore. Il garde **trois** Jobs réussis et **deux** échoués, et
   abandonne une exécution qui aurait plus de **cinq minutes** de retard.
   **Exigence bloquante.**
4. Une exécution de `relance-impayes`, **lancée à la main** sans attendre le
   planning, a réussi.
5. `export-compta` a été **recréé** et a réussi : il exporte la période que
   porte `export-config`.

## 🧭 Les repères utiles

Ne supprimez pas les Pods des Jobs que vous avez réussis : leurs journaux
servent de preuve.

## ✅ Comment vous saurez que c'est bon

Les tests lisent les Jobs, leurs Pods et leurs journaux, et le CronJob. Le
nombre de lots et leurs noms sont tirés au sort à la préparation. Le seuil de
réussite est de 80 %, et les deux exigences bloquantes doivent être tenues.

```bash
dsoxlab check k8s-challenge-executer-et-planifier-des-taches
```
