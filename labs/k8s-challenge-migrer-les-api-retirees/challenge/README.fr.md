# Challenge : Migrer les API retirées avant une montée de version

## 📍 La situation

L'équipe plateforme prépare la prochaine montée de version du cluster. Son
dépôt de manifestes, **`~/plateforme`**, date de plusieurs années : une partie
des fichiers emploie des API que Kubernetes a **retirées**. Personne ne sait
lesquelles. Le namespace **`plateforme`** existe, et rien n'y est appliqué.
Vous êtes sur le control plane, avec `kubectl` configuré.

## 🎯 Ce que vous devez obtenir

1. Un rapport **`~/plateforme/rapport.txt`** qui nomme, à raison d'une ligne
   par fichier, chaque manifeste qui employait une API retirée, sous la forme
   **`<fichier>;<API retirée>;<API de remplacement>`**, par exemple
   `exemple.yaml;batch/v1beta1;batch/v1`. Les fichiers qui n'employaient pas
   d'API retirée n'y figurent pas. **Exigence bloquante.**
2. **Tous** les manifestes du dépôt sont toujours là, et l'API server les
   **accepte tous**. Un fichier se migre, il ne se supprime pas. **Exigence
   bloquante.**
3. Le dépôt migré est **appliqué** : `kubectl diff` sur le dépôt ne trouve
   aucun écart.
4. Les objets décrivent **exactement** ce que décrivaient les manifestes
   hérités : mêmes valeurs, mêmes cibles. Une migration change l'API, pas
   l'intention.
5. Le Deployment `registre` tourne avec ses deux réplicas.

## 🧭 Les repères utiles

Certaines API retirées ont une remplaçante dont les champs n'ont pas tout à
fait la même forme.

## ✅ Comment vous saurez que c'est bon

Les tests confrontent le rapport aux fichiers, soumettent chaque fichier à
l'API server, rejouent `kubectl diff`, puis comparent les objets à ce que
décrivaient les manifestes d'origine. Les fichiers en API retirée sont tirés
au sort à la préparation. Le seuil de réussite est de 80 %, et les deux
exigences bloquantes doivent être tenues.

```bash
dsoxlab check k8s-challenge-migrer-les-api-retirees
```
