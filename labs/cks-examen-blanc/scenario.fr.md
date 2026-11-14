# Examen blanc CKS : 16 tâches en 120 minutes

## Avant de commencer

Cet examen reprend le format de la CKS : des tâches pratiques, notées sur l'état
final du cluster, sans indice. **Prévoyez 120 minutes**, d'un seul tenant, et
lancez votre propre chronomètre : l'outil ne le fait pas. Les tâches sont
indépendantes les unes des autres.

Vous partez de la **base**, `k8s-cp.lab`, la session qu'ouvre `dsoxlab run`.
**Chaque tâche désigne l'hôte où la faire** : connectez-vous par `ssh`,
travaillez, puis revenez à la base par `exit` avant la tâche suivante. Ne
lancez jamais un `ssh` depuis un hôte de tâche. Les deux hôtes, **`k8s-cp.lab`**
et **`k8s-w1.lab`**, ont `kubectl` configuré, l'alias `k` et la complétion, et
votre compte emploie `sudo` sans mot de passe. **Aucun contexte ne fixe le
namespace** : chaque tâche donne le sien, écrivez-le dans vos commandes. Une
ressource créée dans le mauvais namespace ne compte pas.

L'image à employer quand une tâche vous fait créer un Pod :

```text
busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
```

## Les tâches

### Tâche 1 (5 %)

**Connectez-vous : `ssh k8s-w1.lab`** · namespace **`zone`**

Les Pods `db`, `annuaire`, `web` et `intrus` se joignent librement. Refusez
**tout trafic entrant et sortant par défaut** pour chaque Pod du namespace,
puis autorisez seulement : **`web` vers `db` sur le port TCP 80**, et la
**résolution de noms** pour les Pods du namespace (le DNS du cluster, port 53 en
UDP et en TCP). Rien d'autre.

Revenez ensuite à la base : `exit`.

### Tâche 2 (5 %)

**Connectez-vous : `ssh k8s-cp.lab`** · namespace **`vitrine`**

L'Ingress **`site`** publie `vitrine.lab`. Le contrôleur répond déjà en HTTPS
sur le port **30443** du nœud, mais avec son propre certificat par défaut.
Créez un **certificat auto-signé dont le subjectAltName nomme `vitrine.lab`**,
déposez-le dans le Secret TLS **`vitrine-tls`**, et faites servir `vitrine.lab`
en HTTPS par l'Ingress `site` avec ce certificat. Un client qui fait confiance
à ce certificat doit obtenir le site.

Revenez ensuite à la base : `exit`.

### Tâche 3 (5 %)

**Connectez-vous : `ssh k8s-cp.lab`** · aucun namespace (plan de contrôle)

L'audit CIS du plan de contrôle avec kube-bench rend `FAIL` sur les contrôles
de **profilage** de l'**API server**, du **controller manager** et du
**scheduler**. Le Job d'audit est prêt dans **`~/examen/kube-bench-job.yaml`**
(namespace `conformite` ; supprimez un Job terminé avant de le relancer).
Corrigez les trois composants pour qu'un nouvel audit rende ces contrôles
`PASS`, sans casser le plan de contrôle.

Revenez ensuite à la base : `exit`.

### Tâche 4 (10 %)

**Connectez-vous : `ssh k8s-w1.lab`** · namespace **`equipe-dev`**

Le ServiceAccount **`dev-sa`** est lié à `cluster-admin` par le
ClusterRoleBinding **`dev-admin-binding`**. Reprenez ce pouvoir. `dev-sa` garde
**get, list, watch, create, update, patch et delete** sur les **Pods, Services
et Deployments** de `equipe-dev`, par un Role et un RoleBinding de ce
namespace, et **rien d'autre** : aucun Secret, et rien hors de `equipe-dev`.

Revenez ensuite à la base : `exit`.

### Tâche 5 (5 %)

**Connectez-vous : `ssh k8s-w1.lab`** · namespace **`releves`**

Le Deployment **`releveur`** tourne avec le ServiceAccount `default` du
namespace, et ses Pods portent un jeton d'API dont ils ne se servent jamais.
Créez le ServiceAccount **`releveur`**, qui **ne monte jamais son jeton
automatiquement**, et faites-le employer par le Deployment. Le ServiceAccount
`default` de `releves` ne doit plus monter son jeton automatiquement non plus.

Revenez ensuite à la base : `exit`.

### Tâche 6 (5 %)

**Connectez-vous : `ssh k8s-w1.lab`** · namespace **`confinement`**

Sur `k8s-w1.lab`, le fichier de profil AppArmor
**`/etc/apparmor.d/k8s-refuser-ecriture`** existe mais n'est pas chargé.
Chargez-le en mode **enforce**. Créez ensuite le Pod **`confine`** (image
busybox, commande `sleep infinity`) sur `k8s-w1.lab`, confiné par ce profil,
**déclaré dans son `securityContext`**.

Revenez ensuite à la base : `exit`.

### Tâche 7 (5 %)

**Connectez-vous : `ssh k8s-cp.lab`** · namespace **`confinement`**

Sur `k8s-cp.lab`, créez le profil seccomp **`restrict-chmod.json`** dans le
répertoire des profils locaux du kubelet, sous `profiles/` dans
`/var/lib/kubelet/seccomp/`. Il **autorise tout appel par défaut** et **refuse
`chmod`, `fchmod` et `fchmodat`**. Créez ensuite le Pod **`seccomp-pod`**
(image busybox, commande `sleep infinity`) sur `k8s-cp.lab`, avec ce profil. Le
Pod `temoin` doit garder le droit d'appeler `chmod`.

Revenez ensuite à la base : `exit`.

### Tâche 8 (10 %)

**Connectez-vous : `ssh k8s-w1.lab`** · namespace **`durci`**

Le namespace accepte tout : le Pod `laxiste` partage le namespace PID de l'hôte
et tourne en root. Appliquez le standard de sécurité des Pods **`restricted`**
à `durci` dans **les trois modes** (enforce, warn et audit). Créez-y ensuite le
Pod **`conforme`** (image busybox, commande `sleep infinity`) qui satisfait ce
standard. Laissez `laxiste` tranquille.

Revenez ensuite à la base : `exit`.

### Tâche 9 (5 %)

**Connectez-vous : `ssh k8s-w1.lab`** · namespace **`production`**

Le Pod **`insecure-app`** a été créé dans l'urgence. Créez le Pod
**`secure-app`** qui fait le même travail (busybox, commande
`sh -c "sleep 86400"`), **sans aucun de ses défauts** : aucun namespace de
l'hôte, pas de privilège, pas d'escalade de privilèges, un utilisateur non
root, toutes les capabilities retirées, et une image épinglée sur une version.
**Supprimez ensuite `insecure-app`**.

Revenez ensuite à la base : `exit`.

### Tâche 10 (5 %)

**Connectez-vous : `ssh k8s-w1.lab`** · namespace **`tresor`**

Le Deployment **`facturation`** reçoit sa clé d'API dans la variable
d'environnement `CLE_API`, écrite en clair. Rangez cette valeur dans le Secret
**`cle-api`**, clé **`cle`**. Le conteneur doit la lire comme le **fichier en
lecture seule `/etc/tresor/cle`**, et **plus aucune variable d'environnement**
ne doit la porter.

Revenez ensuite à la base : `exit`.

### Tâche 11 (10 %)

**Connectez-vous : `ssh k8s-cp.lab`** · namespace **`chaine`**

Le Deployment **`pinned-app`** désigne son image par le tag `nginx:1.30.5`.
Désignez **cette même image par son seul digest** (`nginx@sha256:...`), celui
que le nœud exécute, sans changer de version. Faites ensuite **refuser** par le
cluster, dans le namespace `chaine` **et là seulement**, la création de tout
Pod dont l'image n'est pas épinglée par digest, avec une
**ValidatingAdmissionPolicy** et sa liaison.

Revenez ensuite à la base : `exit`.

### Tâche 12 (5 %)

**Connectez-vous : `ssh k8s-cp.lab`** · aucun namespace (fichier du nœud)

`trivy config` reproche cinq constats à **`~/examen/inventaire/Dockerfile`** :
`DS-0001`, `DS-0002`, `DS-0004`, `DS-0026` et `DS-0029`. Corrigez le fichier
pour que **ces cinq constats disparaissent**. Il doit toujours partir d'une
image Node et lancer `server.js`. trivy est installé sur `k8s-cp.lab`.

Revenez ensuite à la base : `exit`.

### Tâche 13 (5 %)

**Connectez-vous : `ssh k8s-cp.lab`** · namespace **`chaine-signature`**

Un registre local répond sur `localhost:5000` de `k8s-cp.lab`. Il porte
`localhost:5000/appli/web:1.0` et `localhost:5000/appli/outil:1.0`, et aucune
des deux n'est signée. `cosign` et `crane` sont installés. Générez une paire de
clés dans **`/root`** (un mot de passe vide est accepté), **signez
`appli/web:1.0`** avec elle, et publiez la **clé publique** dans la ConfigMap
**`cosign-pub-key`**, sous la clé **`cosign.pub`**. La clé privée ne quitte pas
le nœud.

Revenez ensuite à la base : `exit`.

### Tâche 14 (10 %)

**Connectez-vous : `ssh k8s-cp.lab`** · namespace **`coffre`**

Faites **enregistrer par l'API server les accès aux Secrets avec le corps
complet** de la requête et de la réponse, et **tout le reste au niveau
`Metadata` seulement**. La politique va dans
**`/etc/kubernetes/audit-policy.yaml`**, le journal dans
**`/var/log/kubernetes/audit.log`**. Le Secret `dossier-medical` de `coffre` est
là pour être lu. L'API server doit toujours répondre ensuite.

Revenez ensuite à la base : `exit`.

### Tâche 15 (5 %)

**Connectez-vous : `ssh k8s-w1.lab`** · namespace **`catalogue`**

Le Deployment **`vitrine`** tourne sous un utilisateur sans privilège, et
pourtant son conteneur peut encore écrire dans son propre système de fichiers,
sa configuration comprise. Rendez ce **système de fichiers en lecture seule**,
interdisez l'**escalade de privilèges**, retirez **toutes les capabilities**,
et déclarez que le processus **ne tourne pas en root**. Le site doit toujours
répondre sur `http://vitrine.catalogue.svc.cluster.local/` depuis le Pod
`client`. Modifiez le Deployment, ne le remplacez pas.

Revenez ensuite à la base : `exit`.

### Tâche 16 (5 %)

**Connectez-vous : `ssh k8s-w1.lab`** · namespace **`atelier`**

Sur `k8s-w1.lab`, **un** des quatre Pods `atelier-1` à `atelier-4` fait tourner
un mineur de cryptomonnaie nommé **`kdevtmpfsi`**, lancé après le Pod lui-même :
leurs specs sont identiques. Trouvez lequel, et **supprimez ce Pod seulement**.

Revenez ensuite à la base : `exit`.

## Comment vous serez noté

Vingt états, à 5 points chacun ; les tâches à 10 % en portent deux. Les poids
suivent ceux des six domaines du programme officiel de la CKS. Le seuil est de
**67 sur 100**, comme à l'examen réel : il faut 14 états sur 20. Aucun indice
n'est proposé, et le retour se limite au verdict, comme le soir de l'examen.

## Ce que cet examen blanc ne reproduit pas

- **Un cluster par tâche** : l'examen réel en enchaîne plusieurs. Ici, les deux
  hôtes pointent sur le même cluster, avec des namespaces différents.
- **Le bureau à distance et son navigateur** limité à la documentation
  officielle.
- **Le chronomètre**, que vous tenez vous-même.
- **Les points partiels** à l'intérieur d'un état : un état est atteint ou non.

```bash
dsoxlab check  cks-examen-blanc
dsoxlab submit cks-examen-blanc
```
