# Cloisonner trois tiers avec des NetworkPolicy ingress et egress

## La situation

Dans le namespace **`lab`**, une application classique en trois tiers :
**`frontend`**, **`backend`** et **`database`**, trois Pods labellisés
`tier=frontend`, `tier=backend` et `tier=database`. Les deux derniers
servent en HTTP sur le port **80**. Aujourd'hui, tout parle à tout, et un
quatrième Pod, **`intrus`**, sans aucun label, atteint la base de données
sans difficulté.

L'équipe sécurité veut que seuls les flux prévus existent : le frontend
parle au backend, le backend parle à la base et résout des noms, et la
base ne parle à personne.

## Ce que vous devez obtenir

1. Une NetworkPolicy **`backend-policy`** sur les Pods `tier=backend` qui
   n'autorise en entrée que les Pods `tier=frontend` sur le port 80, et en
   sortie que les Pods `tier=database` sur le port 80, plus le **DNS** du
   cluster, port 53 en UDP et TCP.

2. Une NetworkPolicy **`database-policy`** sur les Pods `tier=database` qui
   n'autorise en entrée que les Pods `tier=backend` sur le port 80, et
   **aucune sortie**.

3. En vrai : `frontend` joint `backend`, `backend` joint `database` et
   résout des noms, `intrus` ne joint ni `backend` ni `database`, et
   `database` ne joint rien, pas même le DNS.

## Les repères utiles

Une NetworkPolicy ne dit que ce qu'elle autorise, dans les directions
qu'elle déclare sous `policyTypes`. Déclarer `Egress` sans aucune règle
`egress`, c'est interdire toute sortie ; ne pas déclarer `Egress`, c'est ne
rien dire sur la sortie.

Un Pod dont la sortie est restreinte perd le DNS si on ne l'autorise pas
explicitement : le résolveur du cluster est dans `kube-system`, et il écoute
sur le port 53 en UDP et en TCP.

## Comment vous saurez que c'est bon

Les tests lisent les deux politiques, puis font de vraies connexions entre
les Pods, celles qui doivent passer et celles qui doivent échouer.

```bash
dsoxlab check ckad-networkpolicy-ingress-egress
```
