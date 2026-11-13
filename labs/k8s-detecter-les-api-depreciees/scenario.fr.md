# Détecter et migrer les API retirées

## La situation

Une équipe prépare la montée de version de son cluster. Son dépôt de
manifestes, **`~/manifestes`**, date de plusieurs versions : une partie emploie
des API que Kubernetes a **retirées** depuis. Tant qu'ils restent ainsi, ces
fichiers ne s'appliquent plus, et un déploiement automatique casserait le jour de
la montée.

Vous êtes sur **`k8s-cp.lab`**, avec `kubectl` configuré. Le namespace
**`migration`** existe et il est vide : aucun de ces manifestes n'est appliqué.

## Ce que vous devez obtenir

1. **`~/manifestes/rapport.txt`** nomme, un par ligne, les manifestes qui
   employaient une **API retirée**, et eux seuls.
2. Les **six** manifestes du dépôt sont toujours là, et l'API server les
   **accepte tous**. Un fichier se migre, il ne se supprime pas.
3. Les objets migrés sont **appliqués** dans le namespace `migration`.
4. Ils décrivent **exactement** ce que décrivaient les manifestes hérités :
   mêmes valeurs, mêmes cibles. Une migration change l'API, pas l'intention.

## Les repères utiles

- `kubectl apply --dry-run=server -f <fichier>` demande à l'API server s'il
  accepte un manifeste, sans rien créer. Le message d'erreur nomme l'API qu'il
  ne sert plus.
- `kubectl api-resources` et `kubectl explain <type>` disent sous quelle API un
  type est servi aujourd'hui, et quels champs il attend.
- Une API retirée ne change pas toujours que sa version : certains champs ont
  changé de **forme** dans la version courante. Lisez l'erreur jusqu'au bout.

## Comment vous saurez que c'est bon

Les tests lisent le rapport, soumettent chaque fichier à l'API server, puis
comparent les objets du namespace `migration` à ce que décrivaient les
manifestes d'origine.

```bash
dsoxlab check k8s-detecter-les-api-depreciees
```
