# Examen blanc CKA : 17 tâches en 120 minutes

## Avant de commencer

Cet examen reprend le format de la CKA : des tâches pratiques, notées sur l'état
final du cluster, sans indice. **Prévoyez 120 minutes**, d'un seul tenant, et
lancez votre propre chronomètre : l'outil ne le fait pas. Les tâches sont
indépendantes, sauf la tâche 9, qui suppose le nœud de la tâche 3 réparé.

Vous partez de la **base**, `k8s-cp.lab`, la session qu'ouvre `dsoxlab run`.
**Chaque tâche désigne l'hôte où la faire** : connectez-vous par `ssh`,
travaillez, puis revenez à la base par `exit` avant la tâche suivante. Ne
lancez jamais un `ssh` depuis un hôte de tâche. Les deux hôtes, **`k8s-cp.lab`**
et **`k8s-w1.lab`**, ont `kubectl` configuré, l'alias `k` et la complétion.
**Aucun contexte ne fixe le namespace** : chaque tâche donne le sien, écrivez-le
dans vos commandes. Une ressource créée dans le mauvais namespace ne compte pas.

Les images à employer :

```text
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
```

## Les tâches

### Tâche 1 (5 %)

**Connectez-vous : `ssh k8s-cp.lab`** · aucun namespace (ressource du cluster)

Créez la StorageClass **`rapide`**, servie par le provisionneur
`rancher.io/local-path`, qui **garde** ses volumes quand leur revendication
disparaît et ne les crée qu'au moment où un Pod utilise la revendication.

Revenez ensuite à la base : `exit`.

### Tâche 2 (5 %)

**Connectez-vous : `ssh k8s-w1.lab`** · namespace **`appli`**

Créez la revendication **`donnees`** de **100Mi**, en `ReadWriteOnce`, sur la
classe `rapide`. Le Pod **`ecrivain`** (image busybox) la monte sur **`/data`**
et y écrit le fichier **`/data/ok`**, dont le contenu est `ok`.

Revenez ensuite à la base : `exit`.

### Tâche 3 (10 %)

**Connectez-vous : `ssh k8s-w1.lab`** · aucun namespace (ressource du cluster)

Le nœud **`k8s-w1.lab`** est `NotReady`. Remettez-le en service, de façon qu'il
le reste **après un redémarrage**.

Revenez ensuite à la base : `exit`.

### Tâche 4 (5 %)

**Connectez-vous : `ssh k8s-w1.lab`** · namespace **`appli`**

Le Deployment **`facture`** n'arrive pas à démarrer. Réparez-le pour que ses
**deux réplicas** soient prêts. Il doit servir nginx comme l'image le fait
d'elle-même.

Revenez ensuite à la base : `exit`.

### Tâche 5 (10 %)

**Connectez-vous : `ssh k8s-w1.lab`** · namespace **`appli`**

Le Service **`annuaire`** ne mène à aucun Pod. Réparez-le sans toucher au
Deployment `annuaire`, de façon que le Pod **`client`** obtienne la réponse
`annuaire` en interrogeant `http://annuaire/`.

Revenez ensuite à la base : `exit`.

### Tâche 6 (5 %)

**Connectez-vous : `ssh k8s-cp.lab`** · namespace **`appli`**

Écrivez dans **`~/examen/erreurs.txt`** les lignes du journal du conteneur
**`app`** du Pod **`journal`** qui contiennent **`ERROR`**, et elles seules,
une par ligne.

Revenez ensuite à la base : `exit`.

### Tâche 7 (5 %)

**Connectez-vous : `ssh k8s-w1.lab`** · namespace **`appli`**

Mettez à jour le Deployment **`vitrine`** vers l'image **nginx 1.30.6**, puis
ramenez-le à la version précédente par un **retour arrière**.

Revenez ensuite à la base : `exit`.

### Tâche 8 (5 %)

**Connectez-vous : `ssh k8s-w1.lab`** · namespace **`appli`**

Créez la ConfigMap **`reglages`** (clé `mode`, valeur `production`) et le Secret
**`acces`** (clé `mot-de-passe`, valeur `jeton-de-demonstration`). Le conteneur
du Deployment **`api`** doit recevoir la variable **`MODE`** depuis la ConfigMap,
et la variable **`MOT_DE_PASSE`** depuis le Secret.

Revenez ensuite à la base : `exit`.

### Tâche 9 (5 %)

**Connectez-vous : `ssh k8s-cp.lab`** · namespace **`appli`**

Le nœud `k8s-w1.lab` porte le taint `examen=reserve:NoSchedule` et le label
`role-examen=rapports`. Faites tourner **tous** les Pods du Deployment
**`rapport`** sur ce nœud, et seulement sur lui, **sans retirer le taint** et
sans désigner le nœud par son nom. Cette tâche suppose la tâche 3 faite.

Revenez ensuite à la base : `exit`.

### Tâche 10 (10 %)

**Connectez-vous : `ssh k8s-cp.lab`** · namespace **`appli`**

Créez le ServiceAccount **`lecteur`**, et donnez-lui le droit de **lire, lister
et surveiller les Pods** du namespace `appli`, et **rien d'autre**.

Revenez ensuite à la base : `exit`.

### Tâche 11 (5 %)

**Connectez-vous : `ssh k8s-cp.lab`** · aucun namespace (ressource du cluster)

Enregistrez un snapshot d'etcd dans **`/var/lib/etcd/sauvegarde-examen.db`** sur
`k8s-cp.lab`. etcd tourne dans le Pod `etcd-k8s-cp.lab` du namespace
`kube-system`, avec ses certificats sous `/etc/kubernetes/pki/etcd/`.

Revenez ensuite à la base : `exit`.

### Tâche 12 (5 %)

**Connectez-vous : `ssh k8s-cp.lab`** · namespace **`appli`**

Installez la définition **`~/examen/crd-sauvegarde.yaml`**, puis créez dans
`appli` la ressource **`Sauvegarde`** nommée **`quotidienne`**, de source
**`base`** et de rétention **`7`** jours.

Revenez ensuite à la base : `exit`.

### Tâche 13 (5 %)

**Connectez-vous : `ssh k8s-cp.lab`** · namespace **`default`**

Complétez l'overlay **`~/examen/kustomize/overlays/prod/`** pour qu'il place
l'application dans le namespace **`prod`**, avec **3 réplicas** et le label
**`env: prod`** sur le Deployment et ses Pods, puis appliquez-le.

Revenez ensuite à la base : `exit`.

### Tâche 14 (5 %)

**Connectez-vous : `ssh k8s-cp.lab`** · namespace **`reseau`**

Seul le Pod **`front`** doit pouvoir joindre la base **`db`** sur le port
**5432**. Le Pod `autre`, du même namespace, est refusé.

Revenez ensuite à la base : `exit`.

### Tâche 15 (5 %)

**Connectez-vous : `ssh k8s-w1.lab`** · namespace **`reseau`**

Créez l'Ingress **`boutique`**, de classe `traefik`, qui envoie
`http://boutique.examen/api` vers le Service **`api`**. Le contrôleur répond sur
le port **30080** du nœud.

Revenez ensuite à la base : `exit`.

### Tâche 16 (5 %)

**Connectez-vous : `ssh k8s-w1.lab`** · namespace **`reseau`**

Avec la Gateway API, servez l'hôte **`magasin.examen`** par le Service
**`web`** : une Gateway de classe `traefik`, sur le port 80, et une HTTPRoute
nommée **`magasin`**, acceptée par cette Gateway.

Revenez ensuite à la base : `exit`.

### Tâche 17 (5 %)

**Connectez-vous : `ssh k8s-cp.lab`** · namespace **`reseau`**

Publiez le Deployment **`accueil`** (il écoute sur le port 5678) par un Service
**`accueil`** de type **NodePort**, sur le port **30092** de chaque nœud.

Revenez ensuite à la base : `exit`.

## Comment vous serez noté

Vingt états, à 5 points chacun ; les tâches à 10 % en portent deux. Les poids
suivent ceux des domaines du programme officiel de la CKA. Le seuil est de **66
sur 100**, comme à l'examen réel : il faut 14 états sur 20. Aucun indice n'est
proposé, et le retour se limite au verdict, comme le soir de l'examen.

## Ce que cet examen blanc ne reproduit pas

- **Un cluster par tâche** : l'examen réel en enchaîne plusieurs. Ici, les deux
  hôtes visent le même cluster, avec des namespaces différents.
- **Le bureau distant et son navigateur** limité à la documentation officielle.
- **Le chronomètre**, que vous tenez vous-même.
- **La note partielle** à l'intérieur d'un état : un état est réussi ou non.

```bash
dsoxlab check  cka-examen-blanc
dsoxlab submit cka-examen-blanc
```
