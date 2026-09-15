# Rétablir le trafic vers un Service

## La situation

Dans le namespace **`lab`**, le Deployment **`web-app`** tourne en deux
replicas, et chacun de ses Pods répond sur son port 80. Le Service
**`web-svc`** doit les desservir, et pourtant rien ne passe : le Pod
**`client`** du même namespace, qui l'interroge par son nom, n'obtient rien.

Deux choses se sont produites depuis la dernière fois où ça marchait. Un
collègue a « refait le Service ». Et l'équipe sécurité a posé une politique
réseau **`block-all`**, qui ferme tout le trafic entrant du namespace. Cette
politique est **voulue** : elle reste. À vous de rouvrir exactement ce qu'il
faut, et rien de plus.

## Ce que vous devez obtenir

1. `web-svc` a des **endpoints**, et ce sont les Pods de `web-app`.

2. `web-svc` transmet le trafic sur le **port où nginx écoute**.

3. Une NetworkPolicy **`allow-web-ingress`** autorise le trafic entrant vers
   les Pods **`app=web`** sur le **port 80**, depuis n'importe quelle source.
   `block-all` est toujours là.

4. Depuis le Pod `client`, `http://web-svc/` **répond**.

## Les repères utiles

Un Service n'est qu'un selector et des ports. Un Service sans endpoint, c'est
un selector qui ne correspond aux labels d'aucun Pod. Des endpoints mais
rien qui passe, c'est souvent un port. Tout est bon et toujours rien : une
politique bloque.

Les NetworkPolicy s'additionnent : une politique qui ferme tout et une autre
qui ouvre un port précis donnent un port ouvert. Rien n'oblige à retirer la
première.

## Comment vous saurez que c'est bon

Les tests lisent les endpoints du Service, ses ports, les deux politiques, et
ils font réellement une requête depuis le Pod `client`.

```bash
dsoxlab check cka-troubleshoot-networking
```
