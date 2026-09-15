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

3. **Le portail répond sur le port `30080` de chaque nœud**, y compris depuis
   une machine qui n'appartient pas au cluster. C'est l'accès que l'équipe n'a
   jamais mis en place, et c'est par lui que la supervision vérifiera : elle
   interroge les nœuds depuis le réseau, pas depuis l'intérieur du cluster.

4. **Le service d'archives dispose de son stockage.** La réclamation
   `portail-data` doit être effectivement satisfaite, et le Pod `archives`
   doit pouvoir écrire dans `/data`. Une réclamation en attente n'est pas un
   stockage.

5. **Vous ne cassez rien d'autre.** Le cluster doit sortir de là comme il y
   est entré, CoreDNS compris.

## Si vous bloquez

Un micro-lab vous donne ses repères gratuitement. Un capstone, non : trouver
où regarder est justement ce qu'il mesure. Les quatre indices de ce lab vont
du plus vague au plus explicite, ils **coûtent des points**, et le premier ne
nomme aucun des trois défauts : il dit seulement par quoi commencer.

```bash
dsoxlab hint cka-capstone-portail
```

Vous avez donc le choix, comme le jour de l'épreuve : chercher, ou payer pour
être orienté. Les deux sont des réponses légitimes, et votre score les
distingue.

## Comment vous saurez que c'est bon

Les tests lisent l'état du cluster, jamais les commandes tapées. Le dernier
est le seul qui prouve vraiment quelque chose : il interroge le portail depuis
**chacun** des deux nœuds, puis depuis la machine qui pilote le lab, laquelle
n'est pas dans le cluster. C'est ce que fera la supervision.

```bash
dsoxlab check  cka-capstone-portail
dsoxlab submit cka-capstone-portail
```
