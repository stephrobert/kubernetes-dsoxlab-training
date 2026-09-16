# Tout interdire, puis rouvrir le strict nécessaire, DNS compris

## La situation

Dans le namespace **`zero-confiance`**, quatre Pods se parlent librement :
**`db`** sert en HTTP sur le port 80, **`annuaire`** aussi, **`web`** est le
client légitime de la base, et **`intrus`** n'a aucune raison d'y toucher.
Aucune politique réseau n'existe, donc tout le monde joint tout le monde,
`intrus` compris.

L'audit impose le modèle **zéro-confiance** : on ferme tout, puis on rouvre ce
dont l'application a besoin, et **rien d'autre**.

## Ce que vous devez obtenir

1. Le namespace refuse **par défaut** tout trafic entrant et tout trafic
   sortant, pour **tous** ses Pods.

2. Le seul flux applicatif autorisé est **`web` vers `db` sur le port 80**.

3. **Les Pods résolvent toujours les noms.** C'est une exigence à part
   entière : une application qui ne résout plus rien est en panne, même si
   ses flux sont permis.

4. Rien d'autre ne passe. `intrus` ne joint pas `db`, `web` ne joint pas
   `annuaire`, et `db` ne va nulle part de sa propre initiative.

## Les repères utiles

Une NetworkPolicy ne dit que ce qu'elle **autorise**, dans les directions
qu'elle déclare sous `policyTypes`. Déclarer une direction sans écrire la
moindre règle pour elle, c'est l'interdire entièrement ; ne pas la déclarer,
c'est ne rien dire d'elle, donc tout laisser passer.

Un `podSelector` vide sélectionne **tous** les Pods du namespace.

Les politiques se **cumulent** : un Pod est joignable si au moins une règle
l'autorise. Il n'existe pas de règle de refus explicite, ce qui veut dire
qu'une politique trop large ne se corrige pas en ajoutant une interdiction,
mais en la resserrant.

## Comment vous saurez que c'est bon

Les tests font de vraies connexions entre les Pods. Chacun vérifie **les deux
sens** dans la même mesure, parce que sans politique tout passe et qu'après
une coupure générale tout est bloqué : seule la paire dit que le tri se fait.

```bash
dsoxlab check cks-networkpolicy-default-deny
```
