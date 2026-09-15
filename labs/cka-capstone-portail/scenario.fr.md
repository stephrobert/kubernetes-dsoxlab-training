# Capstone : remettre le portail en service, sans personne à qui demander

## La situation

L'équipe qui exploitait le portail est partie. Ce qu'elle laisse tient en une
phrase, reçue par l'astreinte : **« le portail de production ne répond plus »**.
Pas de ticket, pas de journal de changements, personne à appeler.

Tout se passe dans le namespace **`production`**. Ce qui s'y trouve a été
livré dans cet état : il y a des défauts, ils sont indépendants les uns des
autres, et rien ici ne dit lesquels. Les trouver est l'exercice. Corriger un
seul d'entre eux ne fera rien répondre.

Comptez environ **45 minutes**, et traitez cela comme l'épreuve : le seuil de
réussite est de **66 %**. Une exigence entièrement satisfaite vaut mieux que
trois à moitié.

## Ce que l'on attend de vous

1. **Le portail tourne en deux exemplaires**, et les deux sont prêts. Il
   s'appelle `portail`, et son image est la bonne : ce n'est pas elle qu'on
   vous demande de changer.

2. **Le portail répond dans le cluster** au nom `portail-svc`, sur le port
   `80`.

3. **Le portail répond depuis l'extérieur du cluster**, sur le port **30080**
   de **chaque** nœud. C'est l'accès que l'équipe n'a jamais mis en place, et
   c'est par lui que la supervision vérifiera.

4. **Le service d'archives dispose de son stockage.** La réclamation
   `portail-data` doit être effectivement satisfaite, et le Pod `archives`
   doit pouvoir écrire dans `/data`. Une réclamation en attente n'est pas un
   stockage.

5. **Vous ne cassez rien d'autre.** Le cluster doit sortir de là comme il y
   est entré, CoreDNS compris.

## Les repères utiles

Rien ici ne dit où sont les défauts. Ce sont les réflexes qui les trouvent.

- Un Pod qui ne démarre pas raconte toujours pourquoi, mais rarement dans
  `kubectl get`. `kubectl describe pod`, et surtout la section *Events* en bas,
  sont plus bavards, et `kubectl get events --sort-by=.lastTimestamp` donne
  l'ordre des choses.
- Un Service qui ne répond pas a soit aucun endpoint, soit les mauvais.
  `kubectl get endpointslice` dit lequel des deux, et c'est un diagnostic
  différent à chaque fois.
- Un nœud a une quantité finie de CPU et de mémoire, que `kubectl describe
  node` affiche, avec ce qui est déjà réservé.
- Une réclamation de volume en attente cherche quelque chose qui n'existe pas.
  `kubectl describe pvc` dit ce qu'elle cherche.

## Comment vous saurez que c'est bon

Les tests lisent l'état du cluster, jamais les commandes tapées. Le dernier
est le seul qui prouve vraiment quelque chose : il interroge le portail depuis
**chacun** des deux nœuds, comme la supervision le fera.

```bash
dsoxlab check  cka-capstone-portail
dsoxlab submit cka-capstone-portail
```
