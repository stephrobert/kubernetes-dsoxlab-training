# Donner une identité stable à chaque réplica avec un StatefulSet

La leçon montre un StatefulSet : des Pods numérotés, un nom DNS stable par
Pod, et un volume propre à chaque réplica. Ce cours ajoute des cas que la
leçon ne montre pas : une numérotation qui commence à 1, un gabarit de volume
qu'on ne peut plus modifier, un Pod jamais prêt qui bloque les suivants, un
Service qui publie les Pods pas encore prêts, et `minReadySeconds`, qui
ralentit le déploiement.

Vous travaillez dans un namespace d'essai, `essai-sts`, avec trois
StatefulSets d'essai : `registre`, `pair` et `lent`. Chacun a son Service
headless (sans adresse de Service, `clusterIP: None`), qui donne un nom DNS à
chaque Pod. Le challenge porte sur d'autres objets : vous le ferez seul, à la
fin.

Page associée : [StatefulSets](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/statefulsets/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-statefulset-identite-stable
```

Vous êtes maintenant connecté à `k8s-kind.lab`, une machine qui fait tourner
un cluster kind. Votre kubectl le vise déjà. Sa classe de stockage par défaut,
`standard`, crée les volumes à la demande.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.0 (cluster kind).

## 🔢 Exercice 1 : commencer la numérotation à 1

Par défaut, les Pods d'un StatefulSet sont numérotés à partir de 0. Le champ
`ordinals.start` change le premier numéro. Créez le namespace, puis un
StatefulSet `registre` à trois réplicas qui commence à 1. Chaque réplica
reçoit un volume de 64 Mi depuis le gabarit `fiches` :

```bash
kubectl create namespace essai-sts
cat <<YAML | kubectl apply -n essai-sts -f -
apiVersion: v1
kind: Service
metadata:
  name: registre
spec:
  clusterIP: None
  publishNotReadyAddresses: false
  selector: {app: registre}
  ports: [{port: 80}]
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: registre
spec:
  serviceName: registre
  replicas: 3
  ordinals: {start: 1}
  selector:
    matchLabels: {app: registre}
  template:
    metadata:
      labels: {app: registre}
    spec:
      containers:
        - name: web
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
          readinessProbe:
            httpGet: {path: /, port: 80}
            periodSeconds: 2
  volumeClaimTemplates:
    - metadata: {name: fiches}
      spec:
        accessModes: [ReadWriteOnce]
        resources: {requests: {storage: 64Mi}}
YAML
kubectl rollout status statefulset/registre -n essai-sts --timeout=240s; kubectl get pods,pvc -n essai-sts
```

```text
namespace/essai-sts created
service/registre created
statefulset.apps/registre created
Waiting for 3 pods to be ready...
Waiting for 2 pods to be ready...
Waiting for 2 pods to be ready...
Waiting for 1 pods to be ready...
Waiting for 1 pods to be ready...
partitioned roll out complete: 3 new pods have been updated...
NAME             READY   STATUS    RESTARTS   AGE
pod/registre-1   1/1     Running   0          14s
pod/registre-2   1/1     Running   0          10s
pod/registre-3   1/1     Running   0          5s

NAME                                      STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
persistentvolumeclaim/fiches-registre-1   Bound    pvc-ffe860c6-19e3-4a5c-aa75-03b9687bf8df   64Mi       RWO            standard       <unset>                 14s
persistentvolumeclaim/fiches-registre-2   Bound    pvc-57654403-ad18-4e4d-9899-379e3abb074a   64Mi       RWO            standard       <unset>                 10s
persistentvolumeclaim/fiches-registre-3   Bound    pvc-6d0e9fb1-9c2d-4486-aa67-2104414bfccb   64Mi       RWO            standard       <unset>                 5s
```

Les Pods s'appellent `registre-1` à `registre-3`, et chaque demande de volume
porte le nom du gabarit suivi du nom du Pod : `fiches-registre-1`, etc. Les
Pods ont démarré l'un après l'autre (regardez leur âge) : un Pod n'est créé
que quand le précédent est prêt.

## 🔒 Exercice 2 : le gabarit de volume ne se modifie pas

Essayez d'agrandir le gabarit de volume à 128 Mi :

```bash
kubectl patch statefulset registre -n essai-sts --type json -p '[{"op":"replace","path":"/spec/volumeClaimTemplates/0/spec/resources/requests/storage","value":"128Mi"}]'
```

```text
The StatefulSet "registre" is invalid: spec.volumeClaimTemplates: Invalid value: [{"name":"fiches","Spec":{"AccessModes":["ReadWriteOnce"],"Selector":null,"Resources":{"Limits":null,"Requests":{"storage":"128Mi"}},"VolumeName":"","StorageClassName":null,"VolumeMode":"Filesystem","DataSource":null,"DataSourceRef":null,"VolumeAttributesClassName":null},"Status":{"Phase":"Pending","AccessModes":null,"Capacity":null,"Conditions":null,"AllocatedResources":null,"AllocatedResourceStatuses":null,"CurrentVolumeAttributesClassName":null,"ModifyVolumeStatus":null,"HealthStatus":null}}]: field is immutable
```

La fin du message est la seule partie utile : `field is immutable`. Une fois
le StatefulSet créé, `volumeClaimTemplates` ne bouge plus. Pour agrandir les
volumes, il faut agrandir chaque demande existante (si la classe le permet),
ou recréer le StatefulSet.

## 🧱 Exercice 3 : un Pod jamais prêt bloque les suivants

Créez un second StatefulSet, `pair`, dont la sonde de disponibilité vise une
page qui n'existe pas, `/absent` :

```bash
cat <<YAML | kubectl apply -n essai-sts -f -
apiVersion: v1
kind: Service
metadata:
  name: pair
spec:
  clusterIP: None
  publishNotReadyAddresses: false
  selector: {app: pair}
  ports: [{port: 80}]
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: pair
spec:
  serviceName: pair
  replicas: 3
  
  selector:
    matchLabels: {app: pair}
  template:
    metadata:
      labels: {app: pair}
    spec:
      containers:
        - name: web
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
          readinessProbe:
            httpGet: {path: /absent, port: 80}
            periodSeconds: 2
  volumeClaimTemplates:
    - metadata: {name: fiches}
      spec:
        accessModes: [ReadWriteOnce]
        resources: {requests: {storage: 64Mi}}
YAML
sleep 40; kubectl get pods -n essai-sts -l app=pair
```

```text
service/pair created
statefulset.apps/pair created
NAME     READY   STATUS    RESTARTS   AGE
pair-0   0/1     Running   0          40s
```

Après 40 secondes, un seul Pod existe : `pair-0`. Il tourne, mais il n'est pas
prêt, et le StatefulSet attend qu'il le soit pour créer `pair-1`. Lisez son
état et la dernière plainte de la sonde :

```bash
kubectl get pod pair-0 -n essai-sts -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}{"\n"}'; kubectl get events -n essai-sts --field-selector involvedObject.name=pair-0,reason=Unhealthy -o custom-columns=MESSAGE:.message --no-headers | tail -1
```

```text
False
Readiness probe failed: HTTP probe failed with statuscode: 404
```

La sonde reçoit un 404. Avec la politique par défaut (`OrderedReady`), un seul
Pod bloqué arrête tout le démarrage. Quand un StatefulSet reste à un Pod,
regardez d'abord la disponibilité du dernier Pod créé.

## 📣 Exercice 4 : publier les Pods pas encore prêts

Cherchez le nom DNS de `pair-0` depuis un Pod jetable. Le nom finit par un
point, pour que busybox ne parcoure pas sa liste de recherche :

```bash
kubectl run sonde --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-sts --restart=Never --rm -i --quiet -- sh -c 'sleep 2; nslookup pair-0.pair.essai-sts.svc.cluster.local.'; echo "code $?"
```

```text
Server:		10.96.0.10
Address:	10.96.0.10:53

** server can't find pair-0.pair.essai-sts.svc.cluster.local.: NXDOMAIN

** server can't find pair-0.pair.essai-sts.svc.cluster.local.: NXDOMAIN

pod essai-sts/sonde terminated (Error)
code 1
```

`NXDOMAIN` : le nom n'existe pas encore. Le DNS ne publie que les Pods prêts.
Or certaines applications en grappe ont besoin de se trouver avant d'être
prêtes. Le champ `publishNotReadyAddresses` du Service headless change cela :

```bash
kubectl patch service pair -n essai-sts --type merge -p '{"spec":{"publishNotReadyAddresses":true}}'; sleep 5; kubectl run sonde --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-sts --restart=Never --rm -i --quiet -- sh -c 'sleep 2; nslookup pair-0.pair.essai-sts.svc.cluster.local.' | grep -A1 Name
```

```text
service/pair patched
Name:	pair-0.pair.essai-sts.svc.cluster.local
Address: 10.244.0.92
```

Le nom se résout, alors que `pair-0` n'est toujours pas prêt. Ce réglage est
fait pour le Service headless d'un StatefulSet, pas pour un Service qui reçoit
le trafic des clients.

## 🐢 Exercice 5 : minReadySeconds ralentit le déploiement

Supprimez `pair` et créez `lent`, avec `minReadySeconds: 15` : un Pod prêt
n'est compté comme disponible qu'après 15 secondes de disponibilité continue.
Regardez l'état 25 secondes après la création :

```bash
kubectl delete statefulset pair -n essai-sts; cat <<YAML | kubectl apply -n essai-sts -f -
apiVersion: v1
kind: Service
metadata:
  name: lent
spec:
  clusterIP: None
  publishNotReadyAddresses: false
  selector: {app: lent}
  ports: [{port: 80}]
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: lent
spec:
  serviceName: lent
  replicas: 3
  minReadySeconds: 15
  selector:
    matchLabels: {app: lent}
  template:
    metadata:
      labels: {app: lent}
    spec:
      containers:
        - name: web
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
          readinessProbe:
            httpGet: {path: /, port: 80}
            periodSeconds: 2
  volumeClaimTemplates:
    - metadata: {name: fiches}
      spec:
        accessModes: [ReadWriteOnce]
        resources: {requests: {storage: 64Mi}}
YAML
sleep 25; kubectl get pods -n essai-sts -l app=lent; kubectl get statefulset lent -n essai-sts -o jsonpath='prêts={.status.readyReplicas} disponibles={.status.availableReplicas}{"\n"}'
```

```text
statefulset.apps "pair" deleted from essai-sts namespace
service/lent created
statefulset.apps/lent created
NAME     READY   STATUS    RESTARTS   AGE
lent-0   1/1     Running   0          25s
lent-1   0/1     Pending   0          3s
prêts=1 disponibles=1
```

`lent-0` a attendu ses 15 secondes avant que `lent-1` soit créé. `lent-1` est
prêt depuis 5 secondes, mais pas encore disponible : `prêts=2`,
`disponibles=1`. Ce délai laisse le temps de voir un Pod qui démarre bien puis
tombe, avant de passer au suivant.

## 🧹 Nettoyage

Supprimez le namespace d'essai. Les demandes de volume partent avec lui :

```bash
kubectl delete namespace essai-sts
```

```text
namespace "essai-sts" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-statefulset-identite-stable
dsoxlab check cka-statefulset-identite-stable
```

```text
╭─ Résultat : cka-statefulset-identite-stable ─╮
│  0 / 100 pts                                 │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests             │
╰──────────────────────────────────────────────╯
```

0 sur 6 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un annuaire à trois réplicas, chacun avec son nom
et ses données.

```bash
dsoxlab run cka-statefulset-identite-stable
dsoxlab challenge cka-statefulset-identite-stable
```
