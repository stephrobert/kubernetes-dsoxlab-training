# Créer sa StorageClass et obtenir un volume qu'aucun administrateur n'a créé

La leçon montre une StorageClass qui fait créer les volumes à la demande par
un provisionneur. Ce cours éprouve les réglages d'une classe sur le
provisionneur du lab, et ajoute des cas que la leçon ne montre pas : une
classe en `Immediate` qui ne peut pas fonctionner avec ce provisionneur, un
volume qu'on ne peut pas agrandir, un paramètre propre au provisionneur qui
range les volumes autrement, et un volume qui disparaît avec sa demande.

Vous travaillez dans un namespace d'essai, `essai-classe`, avec deux classes
d'essai (`classe-immediate` et `classe-rangee`) et des demandes `carnet`. Le
challenge porte sur d'autres objets : vous le ferez seul, à la fin.

Page associée : [StorageClass](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/storageclass/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-storageclass-provisionnement-dynamique
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2 et local-path-provisioner v0.0.37.

Créez le namespace, puis lisez la classe installée par le lab et ses
réglages :

```bash
kubectl create namespace essai-classe; kubectl get storageclass; kubectl get storageclass local-path -o jsonpath='{.provisioner} {.volumeBindingMode} {.reclaimPolicy} expansion={.allowVolumeExpansion}{"\n"}'
```

```text
namespace/essai-classe created
NAME         PROVISIONER             RECLAIMPOLICY   VOLUMEBINDINGMODE      ALLOWVOLUMEEXPANSION   AGE
local-path   rancher.io/local-path   Delete          WaitForFirstConsumer   false                  5m32s
rancher.io/local-path WaitForFirstConsumer Delete expansion=
```

La classe `local-path` est servie par le provisionneur `rancher.io/local-path`.
Elle crée les volumes au premier Pod qui les utilise (`WaitForFirstConsumer`),
les supprime avec leur demande (`Delete`), et ne permet pas de les agrandir.
Le provisionneur lui-même tourne comme un Deployment :

```bash
kubectl -n local-path-storage get deployment -o jsonpath='{.items[0].spec.template.spec.containers[0].image}{"\n"}'
```

```text
docker.io/rancher/local-path-provisioner:v0.0.37@sha256:e757967a5ec338f6a9b371c5a9688bedaa8c3578ea3dd4db329ea0084be0a86f
```

## ⏱️ Exercice 1 : une classe en Immediate

Créez une classe identique, mais en `volumeBindingMode: Immediate`, et une
demande qui l'utilise, sans aucun Pod :

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: classe-immediate
provisioner: rancher.io/local-path
reclaimPolicy: Delete
volumeBindingMode: Immediate
YAML
cat <<'YAML' | kubectl apply -n essai-classe -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: carnet-immediat
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: classe-immediate
  resources: {requests: {storage: 64Mi}}
YAML
sleep 15; kubectl get pvc carnet-immediat -n essai-classe
```

```text
storageclass.storage.k8s.io/classe-immediate created
persistentvolumeclaim/carnet-immediat created
NAME              STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS       VOLUMEATTRIBUTESCLASS   AGE
carnet-immediat   Pending                                      classe-immediate   <unset>                 15s
```

La demande reste `Pending`. Les événements disent pourquoi :

```bash
kubectl get events -n essai-classe --field-selector involvedObject.name=carnet-immediat -o custom-columns=RAISON:.reason,MESSAGE:.message | tail -3
```

```text
Provisioning           External provisioner is provisioning volume for claim "essai-classe/carnet-immediat"
ProvisioningFailed     failed to provision volume with StorageClass "classe-immediate": configuration error, no node was specified
ExternalProvisioning   Waiting for a volume to be created either by the external provisioner 'rancher.io/local-path' or manually by the system administrator. If volume creation is delayed, please verify that the provisioner is running and correctly registered.
```

`no node was specified` : local-path crée le volume dans un répertoire d'un
nœud, et il doit savoir lequel. En `Immediate`, la demande est traitée avant
qu'un Pod soit placé, donc sans nœud. Avec un stockage local, seule
`WaitForFirstConsumer` fonctionne : le volume est créé sur le nœud du premier
Pod.

## 📏 Exercice 2 : agrandir un volume

Créez une demande de 64 Mi sur `local-path`, et un Pod qui écrit une page
dedans :

```bash
cat <<'YAML' | kubectl apply -n essai-classe -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: carnet
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: local-path
  resources: {requests: {storage: 64Mi}}
YAML
cat <<YAML | kubectl apply -n essai-classe -f -
apiVersion: v1
kind: Pod
metadata:
  name: carnet-pod
spec:
  containers:
    - name: c
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo page 1 > /data/page; sleep 3600"]
      volumeMounts:
        - {name: v, mountPath: /data}
  volumes:
    - name: v
      persistentVolumeClaim: {claimName: carnet}
YAML
kubectl wait --for=condition=Ready pod/carnet-pod -n essai-classe --timeout=120s; kubectl get pvc carnet -n essai-classe
```

```text
persistentvolumeclaim/carnet created
pod/carnet-pod created
pod/carnet-pod condition met
NAME     STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
carnet   Bound    pvc-99a68fa0-462b-4483-83ff-1a4c526b03bd   64Mi       RWO            local-path     <unset>                 5s
```

Demandez maintenant 128 Mi :

```bash
kubectl patch pvc carnet -n essai-classe --type merge -p '{"spec":{"resources":{"requests":{"storage":"128Mi"}}}}'
```

```text
Error from server (Forbidden): persistentvolumeclaims "carnet" is forbidden: only dynamically provisioned pvc can be resized and the storageclass that provisions the pvc must support resize
```

Refusé dès l'envoi : la classe `local-path` n'a pas `allowVolumeExpansion:
true`, comme vous l'avez lu au début. C'est l'API qui refuse, avant tout
provisionneur. Pour un volume qui devra grandir, la classe se choisit à la
création de la demande.

## 🗂️ Exercice 3 : ranger les volumes autrement

Le champ `parameters` d'une classe est transmis au provisionneur, qui seul
sait le lire. local-path accepte `pathPattern`, pour choisir le répertoire de
chaque volume. Créez une classe qui range les volumes par namespace puis par
nom de demande, avec une demande et un Pod :

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: classe-rangee
provisioner: rancher.io/local-path
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
parameters:
  pathPattern: "{{ .PVC.Namespace }}/{{ .PVC.Name }}"
YAML
cat <<'YAML' | kubectl apply -n essai-classe -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: carnet-range
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: classe-rangee
  resources: {requests: {storage: 64Mi}}
YAML
cat <<YAML | kubectl apply -n essai-classe -f -
apiVersion: v1
kind: Pod
metadata:
  name: range-pod
spec:
  containers:
    - name: c
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo range > /data/page; sleep 3600"]
      volumeMounts:
        - {name: v, mountPath: /data}
  volumes:
    - name: v
      persistentVolumeClaim: {claimName: carnet-range}
YAML
sleep 20; kubectl get pvc carnet-range -n essai-classe; kubectl get events -n essai-classe --field-selector involvedObject.name=carnet-range,reason=ProvisioningFailed -o jsonpath='{.items[0].message}{"\n"}'
```

```text
storageclass.storage.k8s.io/classe-rangee created
persistentvolumeclaim/carnet-range created
pod/range-pod created
NAME           STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS    VOLUMEATTRIBUTESCLASS   AGE
carnet-range   Pending                                      classe-rangee   <unset>                 20s
failed to provision volume with StorageClass "classe-rangee": failed to create path from pattern {{ .PVC.Namespace }}/{{ .PVC.Name }}: pathPattern must start with {{ .PVC.Namespace }}/{{ .PVC.Name }}/: essai-classe/carnet-range
```

La demande reste `Pending`, et l'événement `ProvisioningFailed` explique
pourquoi : cette version du provisionneur exige que le modèle commence par
`{{ .PVC.Namespace }}/{{ .PVC.Name }}/`, avec un niveau en dessous. L'API, elle,
a accepté la classe sans rien vérifier : elle ne connaît pas les paramètres
des provisionneurs. Les paramètres d'une classe ne se modifient pas : supprimez
tout et recréez la classe avec un sous-répertoire `donnees` :

```bash
kubectl delete pod range-pod -n essai-classe; kubectl delete pvc carnet-range -n essai-classe; kubectl delete storageclass classe-rangee; cat <<'YAML' | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: classe-rangee
provisioner: rancher.io/local-path
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
parameters:
  pathPattern: "{{ .PVC.Namespace }}/{{ .PVC.Name }}/donnees"
YAML
cat <<'YAML' | kubectl apply -n essai-classe -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: carnet-range
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: classe-rangee
  resources: {requests: {storage: 64Mi}}
YAML
cat <<YAML | kubectl apply -n essai-classe -f -
apiVersion: v1
kind: Pod
metadata:
  name: range-pod
spec:
  containers:
    - name: c
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo range > /data/page; sleep 3600"]
      volumeMounts:
        - {name: v, mountPath: /data}
  volumes:
    - name: v
      persistentVolumeClaim: {claimName: carnet-range}
YAML
kubectl wait --for=condition=Ready pod/range-pod -n essai-classe --timeout=120s
```

```text
pod "range-pod" deleted from essai-classe namespace
persistentvolumeclaim "carnet-range" deleted from essai-classe namespace
storageclass.storage.k8s.io "classe-rangee" deleted
storageclass.storage.k8s.io/classe-rangee created
persistentvolumeclaim/carnet-range created
pod/range-pod created
pod/range-pod condition met
```

Comparez les chemins des deux volumes sur le nœud :

```bash
for p in carnet carnet-range; do V=$(kubectl get pvc $p -n essai-classe -o jsonpath='{.spec.volumeName}'); kubectl get pv $V -o jsonpath='{.metadata.name} -> {.spec.hostPath.path}{.spec.local.path}{"\n"}'; done
```

```text
pvc-99a68fa0-462b-4483-83ff-1a4c526b03bd -> /opt/local-path-provisioner/pvc-99a68fa0-462b-4483-83ff-1a4c526b03bd_essai-classe_carnet
pvc-535fedff-1ef9-4688-8873-d145bce7342d -> /opt/local-path-provisioner/essai-classe/carnet-range/donnees
```

Le premier volume porte le nom par défaut de local-path. Le second suit le
modèle : `essai-classe/carnet-range/donnees`.

## ♻️ Exercice 4 : même nom, volume neuf

Supprimez le Pod et la demande `carnet`, puis cherchez son volume :

```bash
V1=$(kubectl get pvc carnet -n essai-classe -o jsonpath='{.spec.volumeName}'); echo "avant : $V1"; kubectl delete pod carnet-pod -n essai-classe; kubectl delete pvc carnet -n essai-classe; sleep 5; kubectl get pv $V1; echo "pv : code $?"
```

```text
avant : pvc-99a68fa0-462b-4483-83ff-1a4c526b03bd
pod "carnet-pod" deleted from essai-classe namespace
persistentvolumeclaim "carnet" deleted from essai-classe namespace
Error from server (NotFound): persistentvolumes "pvc-99a68fa0-462b-4483-83ff-1a4c526b03bd" not found
pv : code 1
```

Le volume a disparu avec la demande : c'est la politique `Delete` de la
classe. Recréez une demande `carnet` identique, et un Pod qui lit la page
écrite à l'exercice 2 :

```bash
cat <<'YAML' | kubectl apply -n essai-classe -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: carnet
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: local-path
  resources: {requests: {storage: 64Mi}}
YAML
cat <<YAML | kubectl apply -n essai-classe -f -
apiVersion: v1
kind: Pod
metadata:
  name: carnet-pod
spec:
  containers:
    - name: c
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "ls /data; cat /data/page; sleep 3600"]
      volumeMounts:
        - {name: v, mountPath: /data}
  volumes:
    - name: v
      persistentVolumeClaim: {claimName: carnet}
YAML
kubectl wait --for=condition=Ready pod/carnet-pod -n essai-classe --timeout=120s; echo "après : $(kubectl get pvc carnet -n essai-classe -o jsonpath='{.spec.volumeName}')"; kubectl logs carnet-pod -n essai-classe
```

```text
persistentvolumeclaim/carnet created
pod/carnet-pod created
pod/carnet-pod condition met
après : pvc-318a289a-046c-4f91-a070-c0dd9abf4673
cat: can't open '/data/page': No such file or directory
```

Même nom de demande, mais nouveau volume, vide : la page est perdue. Avec
`Delete`, supprimer une demande supprime les données. Pour des données qu'on
veut garder, la classe doit être en `Retain`.

## 🧹 Nettoyage

Supprimez le namespace d'essai et les deux classes, qui n'appartiennent à
aucun namespace :

```bash
kubectl delete namespace essai-classe; kubectl delete storageclass classe-immediate classe-rangee
```

```text
namespace "essai-classe" deleted
storageclass.storage.k8s.io "classe-immediate" deleted
storageclass.storage.k8s.io "classe-rangee" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-storageclass-provisionnement-dynamique
dsoxlab check cka-storageclass-provisionnement-dynamique
```

```text
╭─ Résultat : cka-storageclass-provisionnement-dynamique ─╮
│  0 / 100 pts                                            │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests                        │
╰─────────────────────────────────────────────────────────╯
```

0 sur 6 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : une classe qui garde ses volumes, et un volume créé
pour vous par le provisionneur.

```bash
dsoxlab run cka-storageclass-provisionnement-dynamique
dsoxlab challenge cka-storageclass-provisionnement-dynamique
```
