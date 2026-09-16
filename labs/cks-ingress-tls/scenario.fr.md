# Servir un site en HTTPS avec son propre certificat, et non celui du contrôleur

## La situation

Le site interne **`vitrine.lab`** est publié par le contrôleur Ingress du
cluster. Il répond, et il répond même en HTTPS : l'équipe en a conclu que le
chiffrement était en place et a fermé le ticket.

L'audit vient de rouvrir le ticket. Le contrôleur fabrique un certificat
générique au démarrage et le sert à qui le demande, faute d'en avoir reçu un
autre. Aucun client ne peut donc vérifier qu'il parle bien à `vitrine.lab` :
le certificat ne nomme pas cet hôte, et personne ne l'a signé.

Le site vit dans le namespace **`vitrine`**, derrière un Service et un
Ingress déjà en place.

## Ce que vous devez obtenir

1. Le serveur présente, pour l'hôte `vitrine.lab`, un certificat qui **nomme
   cet hôte**. Il peut être auto-signé : il n'y a pas d'autorité à joindre ici.

2. Le site continue de répondre. Une terminaison TLS qui casse la route ne
   vaut pas mieux que pas de terminaison du tout.

Le contrôleur est déjà installé, ne le touchez pas. Son entrée sécurisée est
exposée sur le port **30443** du nœud.

## Les repères utiles

Ce que le serveur présente se lit sur la connexion elle-même, pas dans un
manifeste :

```bash
echo | openssl s_client -connect 127.0.0.1:30443 -servername vitrine.lab 2>/dev/null \
  | openssl x509 -noout -subject
```

L'option `-servername` envoie le nom demandé. Sans elle, le contrôleur ne sait
pas quel hôte vous voulez et retombe sur son certificat par défaut.

Le certificat et sa clé se déposent dans un objet dont le **type** compte. Un
objet du type générique portant les mêmes clés ne serait lu par personne.

Un certificat qui n'aurait qu'un CN serait refusé par tout client qui vérifie :
les clients TLS ignorent le CN depuis des années et ne valident que le
`subjectAltName`.

Déposer le certificat ne suffit pas : il faut encore **dire à l'Ingress** de
s'en servir, et pour quel hôte.

Le contrôleur recharge sa configuration après avoir été notifié. Laissez-lui
quelques secondes avant de conclure.

## Comment vous saurez que c'est bon

Le dernier test ouvre la connexion et lit le certificat servi, puis vérifie
que le site répond encore. Les deux mesures sont dans le même test : « le site
répond en HTTPS » est déjà vrai avant votre intervention, et ne prouve rien
tout seul.

```bash
dsoxlab check cks-ingress-tls
```
