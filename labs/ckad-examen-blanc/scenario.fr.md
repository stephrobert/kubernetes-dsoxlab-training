# Examen blanc CKAD : 17 tâches en 120 minutes

## Avant de commencer

Cet examen reprend le format de la CKAD : des tâches pratiques, notées sur l'état
final du cluster, sans indice. **Prévoyez 120 minutes**, d'un seul tenant, et
lancez votre propre chronomètre : l'outil ne le fait pas. Les tâches sont
indépendantes.

Vous travaillez sur le control plane **`k8s-cp.lab`**, avec `kubectl`. Votre
kubeconfig contient trois contextes, tous vers le même cluster :
**`ckad-atelier`** (namespace `atelier`), **`ckad-boutique`** (namespace
`boutique`) et **`ckad-securite`** (namespace `securite`). **Chaque tâche commence
par le contexte à utiliser.** Basculez avant de travailler : une ressource créée
dans le mauvais namespace ne compte pas.

Les images à employer :

```text
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
```

## Les tâches

### Tâche 1 (5 %) : contexte `ckad-atelier`

Créez le CronJob **`purge`** (image busybox, commande `echo purge`), qui se
lance **toutes les dix minutes**, garde **deux** exécutions réussies dans son
historique et n'en lance **jamais deux à la fois**.

### Tâche 2 (10 %) : contexte `ckad-atelier`

Créez le Pod **`journal`**. Son conteneur **`app`** (busybox) ajoute une ligne
horodatée au fichier **`/var/log/app/app.log`** toutes les deux secondes. Un
conteneur sidecar **`lecteur`** (busybox) partage ce répertoire par un volume
`emptyDir` et affiche le fichier en continu sur sa sortie standard.

### Tâche 3 (5 %) : contexte `ckad-atelier`

Créez la revendication **`cache`** de **50Mi**, sur la classe `local-path`, et le
Pod **`stockage`** (busybox) qui la monte sur **`/cache`** et y écrit le fichier
**`/cache/ok`**, dont le contenu est `ok`.

### Tâche 4 (10 %) : contexte `ckad-boutique`

La vitrine est servie en version bleue (Deployment `vitrine-bleu`). Basculez-la
en version verte : le Deployment **`vitrine-vert`** fait tourner **trois
réplicas en nginx 1.30.6**, et le Service **`vitrine`** n'envoie plus que vers
eux. Gardez `vitrine-bleu` en place pour un retour arrière.

### Tâche 5 (5 %) : contexte `ckad-boutique`

Mettez à jour le Deployment **`catalogue`** vers **nginx 1.30.6**, avec une
stratégie qui n'ajoute **qu'un Pod à la fois** et n'en retire **aucun** avant que
le nouveau soit prêt.

### Tâche 6 (5 %) : contexte `ckad-boutique`

Complétez l'overlay **`~/examen/kustomize/overlays/boutique/`** pour qu'il place
l'application dans le namespace **`boutique`**, avec **2 réplicas** et l'image
**nginx 1.30.6**, puis appliquez-le.

### Tâche 7 (5 %) : contexte `ckad-atelier`

Ajoutez au Deployment **`api`** une sonde de **disponibilité** HTTP sur `/`, port
80, et une sonde de **vie** TCP sur le port 80. Ses deux Pods doivent rester
prêts.

### Tâche 8 (5 %) : contexte `ckad-atelier`

Le manifeste **`~/examen/pdb-ancien.yaml`** emploie une API retirée de
Kubernetes. Réécrivez-le dans sa version actuelle, sans rien changer à ce qu'il
décrit, et appliquez-le.

### Tâche 9 (5 %) : contexte `ckad-atelier`

Le Pod **`outil`** ne démarre pas. Faites-le tourner sur l'image busybox donnée
plus haut.

### Tâche 10 (5 %) : contexte `ckad-atelier`

Créez la ConfigMap **`parametres`** (clé `app.conf`, contenu `niveau=debug`) et
le Pod **`lecture-config`** (busybox) qui la reçoit en **fichier**,
**`/etc/app/app.conf`**.

### Tâche 11 (5 %) : contexte `ckad-atelier`

Créez le Secret **`jeton`** (clé `valeur`, valeur `jeton-de-demonstration`) et le
Pod **`lecture-secret`** (busybox) qui le reçoit dans la variable **`JETON`**.

### Tâche 12 (5 %) : contexte `ckad-securite`

Créez le Pod **`durci`** (busybox, `sleep infinity`) qui tourne **sous l'uid
1000**, refuse de tourner en root, a un système de fichiers racine en **lecture
seule**, ne peut pas **élever ses privilèges** et a retiré **toutes** ses
capacités.

### Tâche 13 (5 %) : contexte `ckad-securite`

Posez le quota **`plafond`** : 5 Pods au plus, 2 CPU et 1Gi de mémoire en
limites. Puis créez le Pod **`mesure`** (busybox, `sleep infinity`) qui demande
100m de CPU et 64Mi de mémoire, limité à 200m et 128Mi, et qui tient dans ce
quota.

### Tâche 14 (5 %) : contexte `ckad-securite`

Créez le ServiceAccount **`deployeur`** et le Pod **`outil-sa`** (busybox,
`sleep infinity`) qui tourne sous ce compte, **sans** que le jeton du compte soit
monté dans le Pod.

### Tâche 15 (5 %) : contexte `ckad-boutique`

Seul le Pod **`front`** doit pouvoir joindre le Pod **`interne`** (port 5678). Le
Pod `autre` est refusé.

### Tâche 16 (10 %) : contexte `ckad-boutique`

Le Service **`stock`** ne mène à aucun Pod. Réparez-le, sans toucher au
Deployment `stock`, pour que le Pod `front` obtienne la réponse `stock` en
interrogeant `http://stock/`.

### Tâche 17 (5 %) : contexte `ckad-boutique`

Créez l'Ingress **`infos`**, de classe `traefik`, qui envoie
`http://infos.examen/infos` vers le Service **`infos`**. Le contrôleur répond
sur le port **30080** du nœud.

## Comment vous serez noté

Vingt états, à 5 points chacun ; les tâches à 10 % en portent deux. Les poids
suivent ceux des domaines du programme officiel de la CKAD. Le seuil est de **66
sur 100**, comme à l'examen réel : il faut 14 états sur 20. Aucun indice n'est
proposé, et le retour se limite au verdict, comme le soir de l'examen.

## Ce que cet examen blanc ne reproduit pas

- **Un cluster par tâche** : l'examen réel en enchaîne plusieurs. Ici, les trois
  contextes visent le même cluster, avec des namespaces différents.
- **Le bureau distant et son navigateur** limité à la documentation officielle.
- **Le chronomètre**, que vous tenez vous-même.
- **La note partielle** à l'intérieur d'un état : un état est réussi ou non.
- **Helm et la construction d'images**, que le programme cite et que la
  formation enseigne ailleurs.

```bash
dsoxlab check  ckad-examen-blanc
dsoxlab submit ckad-examen-blanc
```
