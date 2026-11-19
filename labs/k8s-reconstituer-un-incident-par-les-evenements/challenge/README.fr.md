# Challenge : Reconstituer un incident à partir des Events d'un namespace

## La situation

Il y a quelques minutes, la boutique en ligne a commencé à mal répondre. Dans
le namespace **`boutique`** tournent cinq applications : **`panier`**,
**`paiement`**, **`catalogue`**, **`stock`** et **`avis`**. D'après l'équipe,
plusieurs sont tombées, l'une après l'autre.

Avant que quiconque ne répare quoi que ce soit, on vous demande le **rapport
d'incident**. **Ne réparez rien** : le rapport décrit ce qui s'est passé.

Vous êtes sur le control plane, avec `kubectl` configuré.

## Ce que vous devez obtenir

Un ConfigMap **`rapport`** dans le namespace `boutique`, avec :

1. **une clé par application** (`panier`, `paiement`, `catalogue`, `stock`,
   `avis`). Sa valeur est la **raison** (`reason`) de ses Events `Warning`,
   écrite mot pour mot ; pour une application qui n'a **aucun** Event
   `Warning`, la valeur est **`aucune`** ;
2. une clé **`premiere-touchee`** : le nom de l'application concernée par le
   **premier** Event `Warning` du namespace.

## Les repères

Un Event concerne un objet précis : ici, les Pods. Le nom d'un Pod d'un
Deployment commence par le nom du Deployment.

`kubectl events` filtre par type (`--types`) et par objet (`--for`).
`kubectl get events` filtre par champ (`--field-selector`) et trie
(`--sort-by`). Un même Event existe sous deux représentations, `v1` et
`events.k8s.io/v1`, dont les noms de champs diffèrent : un tri ou un
`jsonpath` écrit pour l'une ne marche pas forcément sur l'autre.

Les Events ne vivent qu'**une heure** : passé ce délai, ils disparaissent.

## Comment vous saurez que ça marche

Les tests déduisent la panne de chaque application de sa spec, lisent
eux-mêmes les Events Warning du namespace pour trouver le premier, puis
comparent avec votre rapport.

```bash
dsoxlab check k8s-reconstituer-un-incident-par-les-evenements
```
