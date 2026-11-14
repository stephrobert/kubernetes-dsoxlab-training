# Repérer et retirer ce qu'un attaquant a laissé derrière lui

## La situation

La semaine dernière, un attaquant est entré dans le namespace **`facturation`**
du cluster kubeadm par un Pod de débogage, **`outil-debug`**. L'équipe a révoqué
le jeton qu'il utilisait et a cru l'incident clos. Pourtant, le compte sous
lequel il tournait, **`support-n2`**, lit toujours les Secrets de tous les
namespaces : ce qu'on retire à la main revient une minute plus tard.

L'attaquant a laissé plus qu'un accès : quelque chose, dans le namespace, **le
recrée**. À côté tourne l'**application légitime** `facturation` : deux réplicas
derrière un Service, sa propre identité `facturation`, sa liaison
`facturation-lecture` et un CronJob de nuit, `purge-factures`. Rien de tout cela
ne doit être abîmé.

Vous êtes sur le plan de contrôle, avec `kubectl` configuré, en root.

## Ce que vous devez obtenir

1. L'objet qui recrée l'accès est **consigné** dans
   **`/root/constat-persistance.yaml`**, exporté de l'objet vivant, **avant toute
   suppression**.
2. Cet objet est **supprimé**, avec ce qu'il a déjà lancé.
3. Les **identités de l'attaquant** et leurs **liaisons à l'échelle du cluster**
   ont disparu : `support-n2` ne lit plus les Secrets du cluster.
4. Le Pod d'origine **`outil-debug`** est supprimé, et l'accès **ne revient pas**
   après la minute de planification suivante.
5. L'**application légitime** est intacte : réplicas, identité, liaison, son
   propre CronJob, et elle répond sur son Service.

## La méthode, pas à pas

**Lister ce qui tourne tout seul.** Une persistance doit survivre au départ de
l'attaquant, elle se relance donc d'elle-même : `kubectl get
cronjobs,daemonsets,jobs -n facturation`, puis la même chose sur tout le cluster
avec `-A`. Un nom anodin ne prouve rien : lisez ce que chacun exécute (`kubectl
get cronjob <nom> -o yaml`, la `command` et le `serviceAccountName`).

Un webhook d'admission est une autre cachette : il voit chaque objet créé.
`kubectl get mutatingwebhookconfigurations,validatingwebhookconfigurations`
les liste, et chacun nomme le service qu'il appelle.

**Lister qui a quels droits.** `kubectl get clusterrolebindings -o wide` montre
chaque sujet lié pour tout le cluster ; un compte d'un namespace applicatif n'a
rien à y faire. `kubectl auth can-i --list --as
system:serviceaccount:facturation:<compte>` dit ce qu'une identité peut faire,
et `kubectl get clusterrole <nom> -o yaml` ce qu'un rôle accorde. Le verbe
`bind` mérite l'attention : il permet de distribuer un rôle qu'on ne détient pas.

**Lire ce qui a changé récemment.** `kubectl get events -n facturation
--sort-by=.lastTimestamp` montre des Jobs créés chaque minute. Sur un cluster
dont l'API server écrit un journal d'audit (lab `cks-audit-log-policy`), le
journal dit quelle identité a créé `support-n2` et quand : `jq
'select(.objectRef.name == "support-n2")'` sur le fichier du journal. Le
cluster de ce lab n'audite rien par défaut : les événements et les objets
eux-mêmes sont ici vos preuves.

**Consigner avant de retirer.** `kubectl get <type> <nom> -o yaml >
/root/constat-persistance.yaml` garde l'objet tel que le cluster le connaît,
avec son UID. Une fois supprimé, plus rien ne dit ce qu'il faisait.

**Retirer dans le bon ordre.** D'abord le mécanisme, ensuite ce qu'il accorde :
supprimer `support-n2` pendant que son créateur tourne ne dure qu'une minute.
Puis l'identité qui donnait ses droits au mécanisme, puis l'accès lui-même, et
enfin le Pod d'origine. Supprimez les objets par leur nom, un par un : supprimer
le namespace, ou tous les CronJobs, emporterait l'application légitime.

**Vérifier que rien ne revient.** Attendez la minute suivante, puis reposez la
question `kubectl auth can-i list secrets -A --as
system:serviceaccount:facturation:support-n2`.

## Comment vous saurez que ça marche

Les tests lisent le fichier de constat et le comparent à l'UID de l'objet posé
par le setup, cherchent le CronJob, ses Jobs et les liaisons de l'attaquant,
attendent au-delà de la minute de planification suivante avant de juger que
l'accès a disparu, puis contrôlent l'application légitime, jusqu'à une vraie
requête HTTP sur son Service.

```bash
dsoxlab check k8s-detecter-une-persistance
```
