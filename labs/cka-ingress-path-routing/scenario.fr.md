# Router deux applications sur un seul hôte, et prouver que chacune reçoit la sienne

## La situation

Deux applications vivent dans le namespace **`lab`** et servent déjà : l'API et
le site. Chacune a son Service, `svc-api` et `svc-web`, sur le port `80`.

L'équipe ne dispose que d'un seul nom d'hôte, **`app.local`**, et doit publier
les deux derrière lui. Aujourd'hui rien ne le fait : le contrôleur Ingress
écoute, mais aucune règle ne lui dit où envoyer quoi.

Chaque application répond son propre nom, ce qui vous permettra de vérifier
sans ambiguïté laquelle a répondu.

## Ce que vous devez obtenir

Pour l'hôte `app.local` :

1. Les requêtes dont le chemin commence par **`/api`** atteignent `svc-api`.

2. Les requêtes dont le chemin commence par **`/web`** atteignent `svc-web`.

3. Un chemin que vous n'avez pas déclaré n'atteint **ni l'une ni l'autre**.

Le contrôleur est déjà installé, ne le touchez pas. Son entrée HTTP est
exposée sur le port **30080** du nœud.

## Les repères utiles

Rien n'étant publié, les requêtes se font en indiquant à `curl` où joindre
l'hôte :

```bash
curl -s --resolve app.local:30080:127.0.0.1 http://app.local:30080/api
```

L'objet qui décrit ces règles vit dans le **même namespace** que les Services
qu'il route. Ce n'est pas un détail : il ne peut pas en désigner un autre.

Un tel objet qui ne désigne aucune **classe** n'est servi par aucun
contrôleur, sauf si une classe par défaut existe.

Le **type de chemin** compte : celui qui compare un préfixe accepte `/api`
comme `/api/v1`, tandis que celui qui compare exactement n'accepterait que
`/api`.

Le contrôleur recharge sa configuration après avoir été notifié. Laissez-lui
quelques secondes.

## Comment vous saurez que c'est bon

Le dernier test interroge les **trois** chemins. Le troisième est le contrôle :
une règle unique qui enverrait tout vers un seul service passerait les deux
premières mesures sans router quoi que ce soit.

```bash
dsoxlab check cka-ingress-path-routing
```
