# Un volume persistant : PersistentVolume, PersistentVolumeClaim et un Pod qui écrit

La leçon montre un PersistentVolume (PV) créé à la main, une demande
PersistentVolumeClaim (PVC) qui s'y lie, et un Pod qui écrit dedans. Ce cours
ajoute des cas que la leçon ne montre pas : choisir un PV précis par une
étiquette, recevoir plus que ce qu'on demande, partager un volume entre deux
Pods par sous-répertoires, monter un volume en lecture seule, et supprimer un
PVC encore utilisé.

Vous travaillez dans un namespace d'essai, `essai-stock`, avec deux PV
(`pv-rapide` et `pv-lent`) et un PVC `reserve`. Les PV écrivent sur le disque
du worker `k8s-w1.lab`, sous `/tmp`. Le challenge porte sur d'autres objets :
vous le ferez seul, à la fin.

Page associée : [Stockage dans Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/storage/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-pv-pvc-storageclass
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà. Le cluster n'a aucun
provisionneur de stockage : chaque PV se crée à la main.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

Créez le namespace et deux PV identiques de 2 Gi, qui ne diffèrent que par
l'étiquette `niveau`. Ils utilisent un répertoire du worker (`hostPath`), et
`nodeAffinity` oblige tout Pod qui s'en sert à tourner sur ce worker :

```bash
kubectl create namespace essai-stock; for n in rapide lent; do cat <<YAML | kubectl apply -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-$n
  labels: {niveau: $n}
spec:
  capacity: {storage: 2Gi}
  accessModes: [ReadWriteOnce]
  storageClassName: essai
  persistentVolumeReclaimPolicy: Retain
  hostPath: {path: /tmp/essai-stock-$n, type: DirectoryOrCreate}
  nodeAffinity:
    required:
      nodeSelectorTerms:
        - matchExpressions:
            - {key: kubernetes.io/hostname, operator: In, values: [k8s-w1.lab]}
YAML
done; kubectl get pv pv-rapide pv-lent
```

```text
namespace/essai-stock created
persistentvolume/pv-rapide created
persistentvolume/pv-lent created
NAME        CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS      CLAIM   STORAGECLASS   VOLUMEATTRIBUTESCLASS   REASON   AGE
pv-rapide   2Gi        RWO            Retain           Available           essai          <unset>                          0s
pv-lent     2Gi        RWO            Retain           Available           essai          <unset>                          0s
```

Les deux PV sont `Available` : libres, en attente d'une demande. Leur classe
`essai` n'existe pas en tant qu'objet : c'est une simple étiquette qui
apparie les PV et les PVC qui portent le même nom.

## 🎯 Exercice 1 : choisir son PV par une étiquette

Un PVC peut porter un `selector`, pour ne se lier qu'à un PV qui porte
certaines étiquettes. Demandez 500 Mi, sur un PV `niveau: lent` :

```bash
cat <<'YAML' | kubectl apply -n essai-stock -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: reserve
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: essai
  resources: {requests: {storage: 500Mi}}
  selector:
    matchLabels: {niveau: lent}
YAML
sleep 3; kubectl get pvc reserve -n essai-stock; kubectl get pv pv-rapide pv-lent
```

```text
persistentvolumeclaim/reserve created
NAME      STATUS   VOLUME    CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
reserve   Bound    pv-lent   2Gi        RWO            essai          <unset>                 3s
NAME        CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS      CLAIM                 STORAGECLASS   VOLUMEATTRIBUTESCLASS   REASON   AGE
pv-rapide   2Gi        RWO            Retain           Available                         essai          <unset>                          3s
pv-lent     2Gi        RWO            Retain           Bound       essai-stock/reserve   essai          <unset>                          3s
```

Le PVC s'est lié à `pv-lent`, et `pv-rapide` reste libre. Sans `selector`,
Kubernetes aurait pris l'un des deux, sans que vous puissiez dire lequel.

## 📏 Exercice 2 : on demande 500 Mi, on reçoit 2 Gi

Comparez la taille demandée et la taille obtenue :

```bash
kubectl get pvc reserve -n essai-stock -o jsonpath='demandé {.spec.resources.requests.storage}, lié {.status.capacity.storage}{"\n"}'
```

```text
demandé 500Mi, lié 2Gi
```

Un PV se lie en entier à un seul PVC. Le PVC reçoit donc toute la capacité du
PV, même s'il en demandait moins. Avec des PV créés à la main, prévoyez des
tailles proches des demandes, sinon de l'espace reste réservé sans servir.

## 📂 Exercice 3 : deux Pods, un volume, deux sous-répertoires

Le champ `subPath` monte un sous-répertoire du volume au lieu de sa racine.
Créez deux Pods qui montent le même PVC, chacun dans son sous-répertoire, et
qui y écrivent une note :

```bash
for a in a b; do cat <<YAML | kubectl apply -n essai-stock -f -
apiVersion: v1
kind: Pod
metadata:
  name: atelier-$a
spec:
  containers:
    - name: atelier
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo ecrit par atelier-$a > /travail/note; sleep 3600"]
      volumeMounts:
        - {name: v, mountPath: /travail, subPath: atelier-$a}
  volumes:
    - name: v
      persistentVolumeClaim: {claimName: reserve}
YAML
done; kubectl wait --for=condition=Ready pod/atelier-a pod/atelier-b -n essai-stock --timeout=120s
```

```text
pod/atelier-a created
pod/atelier-b created
pod/atelier-a condition met
pod/atelier-b condition met
```

Lisez la note de chacun, puis l'arborescence complète du volume, avec un Pod
jetable qui le monte à la racine (`--rm` le supprime à la fin) :

```bash
for a in a b; do kubectl exec atelier-$a -n essai-stock -- cat /travail/note; done; kubectl run inventaire --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-stock --restart=Never --rm -i --quiet --overrides='{"spec":{"containers":[{"name":"inventaire","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sh","-c","ls -R /tout"],"volumeMounts":[{"name":"v","mountPath":"/tout"}]}],"volumes":[{"name":"v","persistentVolumeClaim":{"claimName":"reserve"}}]}}'
```

```text
ecrit par atelier-a
ecrit par atelier-b
/tout:
atelier-a
atelier-b

/tout/atelier-a:
note

/tout/atelier-b:
note
```

Chaque Pod ne voit que son répertoire, mais les deux sont sur le même volume.
Les sous-répertoires ont été créés au premier montage. Les deux Pods partagent
un PV en `ReadWriteOnce` parce qu'ils tournent sur le même nœud : ce mode
limite le volume à un nœud, pas à un Pod.

## 🔏 Exercice 4 : un montage en lecture seule

Créez un Pod qui monte le volume en lecture seule, puis qui lit une note et
essaie d'écrire :

```bash
cat <<YAML | kubectl apply -n essai-stock -f -
apiVersion: v1
kind: Pod
metadata:
  name: lecteur
spec:
  containers:
    - name: lecteur
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "3600"]
      volumeMounts:
        - {name: v, mountPath: /lecture, readOnly: true}
  volumes:
    - name: v
      persistentVolumeClaim: {claimName: reserve, readOnly: true}
YAML
kubectl wait --for=condition=Ready pod/lecteur -n essai-stock --timeout=120s; kubectl exec lecteur -n essai-stock -- cat /lecture/atelier-a/note; kubectl exec lecteur -n essai-stock -- sh -c 'echo essai > /lecture/x'; echo "écriture : code $?"
```

```text
pod/lecteur created
pod/lecteur condition met
ecrit par atelier-a
sh: line 0: can't create /lecture/x: Read-only file system
command terminated with exit code 1
écriture : code 1
```

La lecture marche, l'écriture est refusée par le noyau (`Read-only file
system`). Un Pod qui n'a qu'à lire ne doit pas pouvoir abîmer les données
des autres.

## 🗑️ Exercice 5 : supprimer un PVC encore utilisé

Supprimez le PVC pendant que trois Pods s'en servent :

```bash
kubectl delete pvc reserve -n essai-stock --wait=false; sleep 3; kubectl get pvc reserve -n essai-stock; kubectl get pvc reserve -n essai-stock -o jsonpath='{.metadata.finalizers}{"\n"}'
```

```text
persistentvolumeclaim "reserve" deleted from essai-stock namespace
NAME      STATUS        VOLUME    CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
reserve   Terminating   pv-lent   2Gi        RWO            essai          <unset>                 11s
["kubernetes.io/pvc-protection"]
```

Le PVC reste en `Terminating`, retenu par le finalizer
`kubernetes.io/pvc-protection` : Kubernetes ne retire pas un volume sous un
Pod qui l'utilise. Supprimez les Pods :

```bash
kubectl delete pod atelier-a atelier-b lecteur -n essai-stock --wait=true; sleep 3; kubectl get pvc -n essai-stock; kubectl get pv pv-lent
```

```text
pod "atelier-a" deleted from essai-stock namespace
pod "atelier-b" deleted from essai-stock namespace
pod "lecteur" deleted from essai-stock namespace
No resources found in essai-stock namespace.
NAME      CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS     CLAIM                 STORAGECLASS   VOLUMEATTRIBUTESCLASS   REASON   AGE
pv-lent   2Gi        RWO            Retain           Released   essai-stock/reserve   essai          <unset>                          45s
```

Une fois les Pods partis, le PVC a disparu. Le PV, lui, est passé en
`Released` : sa politique `Retain` garde les données, mais il ne se liera pas
à une nouvelle demande. Il faut l'examiner, puis le supprimer ou le remettre
en service à la main.

## 🧹 Nettoyage

Supprimez le namespace et les deux PV, puis effacez leurs répertoires sur le
worker. Le PV est en `Retain` : supprimer le PV ne touche pas aux fichiers.

```bash
kubectl delete namespace essai-stock; kubectl delete pv pv-rapide pv-lent; ssh -o StrictHostKeyChecking=no k8s-w1.lab sudo rm -rf /tmp/essai-stock-rapide /tmp/essai-stock-lent; echo "ssh : code $?"
```

```text
namespace "essai-stock" deleted
persistentvolume "pv-rapide" deleted
persistentvolume "pv-lent" deleted
Warning: Permanently added 'k8s-w1.lab' (ED25519) to the list of known hosts.
ssh : code 0
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-pv-pvc-storageclass
dsoxlab check cka-pv-pvc-storageclass
```

```text
╭─ Résultat : cka-pv-pvc-storageclass ─╮
│  0 / 100 pts                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/11 tests    │
╰──────────────────────────────────────╯
```

0 sur 11 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un PV, une demande qui s'y lie, et un Pod dont les
données survivent à sa suppression.

```bash
dsoxlab run cka-pv-pvc-storageclass
dsoxlab challenge cka-pv-pvc-storageclass
```
