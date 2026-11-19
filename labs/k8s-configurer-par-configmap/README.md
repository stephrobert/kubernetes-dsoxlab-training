# Configure an application with a ConfigMap

A good container image does not hold its settings: the same image is used in
test and in production, with different settings. Kubernetes keeps these
settings in a separate object, the **ConfigMap**, and hands them to the
container in two ways: as **environment variables**, or as **files** in a
directory. In this course, you create ConfigMaps, you give them to an
application, then you measure what gets updated, and when, after a change.

You work in a scratch namespace, `essai-config`, with a `meteo` application.
The challenge will ask you for the same work on another application: you will
do it on your own, at the end.

Related page: [Kubernetes ConfigMaps](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/configmaps/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-configurer-par-configmap
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster
`boutique` is running there, and your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026.

## 📚 Exercise 1: a ConfigMap from values

Create the scratch namespace, then a ConfigMap `meteo-reglages` with two
values. Each `--from-literal` adds a `key=value` pair:

```bash
kubectl create namespace essai-config
kubectl create configmap meteo-reglages --from-literal=VILLE=Lyon --from-literal=UNITE=celsius -n essai-config
kubectl get configmap meteo-reglages -n essai-config -o jsonpath='{.data}{"\n"}'
```

```text
namespace/essai-config created
configmap/meteo-reglages created
{"UNITE":"celsius","VILLE":"Lyon"}
```

The settings are stored in the `data` field of the ConfigMap.

## 📚 Exercise 2: a ConfigMap from a file

A setting can also be a whole file. Write a small configuration file, then
create a ConfigMap from it with `--from-file`:

```bash
printf 'station=lyon-bron\nfrequence=10\n' > ~/station.conf; cat ~/station.conf
kubectl create configmap meteo-fichier --from-file=$HOME/station.conf -n essai-config
kubectl describe configmap meteo-fichier -n essai-config | sed -n '/^Data/,/^BinaryData/p'
```

```text
station=lyon-bron
frequence=10
configmap/meteo-fichier created
Data
====
station.conf:
----
station=lyon-bron
frequence=10



BinaryData
```

The **file name**, `station.conf`, became the key, and its content the value.
(`sed` keeps only the `Data` part of the `describe` output.)

## 📚 Exercise 3: give the ConfigMaps to the application

The `meteo` Deployment receives both ConfigMaps, in three ways:

- `envFrom`: each key of `meteo-reglages` becomes an environment variable;
- a volume mounted **as a directory** on `/etc/meteo`: each key of
  `meteo-fichier` becomes a file in it;
- the same volume, mounted with `subPath` on `/etc/station.conf`: a single
  file, put at a precise place.

Its container only sleeps: we only come to read what it sees.

```bash
cat <<'YAML' | kubectl apply -n essai-config -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: meteo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: meteo
  template:
    metadata:
      labels:
        app: meteo
    spec:
      terminationGracePeriodSeconds: 2
      containers:
        - name: meteo
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sleep", "86400"]
          envFrom:
            - configMapRef:
                name: meteo-reglages
          volumeMounts:
            - name: fichier
              mountPath: /etc/meteo
            - name: fichier
              mountPath: /etc/station.conf
              subPath: station.conf
      volumes:
        - name: fichier
          configMap:
            name: meteo-fichier
YAML
kubectl rollout status deployment/meteo -n essai-config --timeout=120s | tail -1
```

```text
deployment.apps/meteo created
deployment "meteo" successfully rolled out
```

Always check from the container: the spec says what is asked, the container
says what is seen. `kubectl exec deploy/meteo` enters a Pod of the Deployment:

```bash
kubectl exec deploy/meteo -n essai-config -- sh -c 'echo VILLE=$VILLE UNITE=$UNITE'
kubectl exec deploy/meteo -n essai-config -- ls /etc/meteo
kubectl exec deploy/meteo -n essai-config -- cat /etc/meteo/station.conf /etc/station.conf
```

```text
VILLE=Lyon UNITE=celsius
station.conf
station=lyon-bron
frequence=10
station=lyon-bron
frequence=10
```

Both variables are there, and the file too, at both places.

## 📚 Exercise 4: change a value

Set `UNITE` to `fahrenheit` in the ConfigMap:

```bash
kubectl patch configmap meteo-reglages -n essai-config -p '{"data":{"UNITE":"fahrenheit"}}'
kubectl get configmap meteo-reglages -n essai-config -o jsonpath='{.data.UNITE}{"\n"}'
kubectl exec deploy/meteo -n essai-config -- sh -c 'echo UNITE=$UNITE'
```

```text
configmap/meteo-reglages patched
fahrenheit
UNITE=celsius
```

The ConfigMap says `fahrenheit`, but the container still sees `celsius`. An
environment variable is read **only once**, when the container starts. Then it
stays frozen.

## 📚 Exercise 5: change the file

Edit the file, then replace the ConfigMap with the new version.
`--dry-run=client -o yaml` builds the new ConfigMap without creating it, and
`kubectl replace` replaces the old one:

```bash
printf 'station=lyon-bron\nfrequence=5\n' > ~/station.conf; kubectl create configmap meteo-fichier --from-file=$HOME/station.conf -n essai-config --dry-run=client -o yaml | kubectl replace -f -
```

```text
configmap/meteo-fichier replaced
```

Measure how long the directory takes to update. The loop reads the file every
5 seconds, until it finds `frequence=5` ("dossier à jour après" means
"directory updated after"):

```bash
debut=$SECONDS; until kubectl exec deploy/meteo -n essai-config -- grep -q frequence=5 /etc/meteo/station.conf 2>/dev/null; do sleep 5; done; echo "dossier à jour après $((SECONDS - debut)) s"
```

```text
dossier à jour après 71 s
```

The directory updates **by itself**, but with a delay, here 71 seconds:
Kubernetes only reads ConfigMaps again at regular intervals. Now compare both
places:

```bash
kubectl exec deploy/meteo -n essai-config -- cat /etc/meteo/station.conf /etc/station.conf
```

```text
station=lyon-bron
frequence=5
station=lyon-bron
frequence=10
```

The file in the directory says `frequence=5`. The one put by `subPath` still
says `frequence=10`: a `subPath` mount is **never** updated.

## 📚 Exercise 6: restart to read everything again

`kubectl rollout restart` replaces the Pods of the Deployment. The new
containers read everything again when they start:

```bash
kubectl rollout restart deployment/meteo -n essai-config
kubectl rollout status deployment/meteo -n essai-config --timeout=120s | tail -1
sleep 3; kubectl exec deploy/meteo -n essai-config -- sh -c 'echo UNITE=$UNITE; cat /etc/station.conf'
```

```text
deployment.apps/meteo restarted
deployment "meteo" successfully rolled out
UNITE=fahrenheit
station=lyon-bron
frequence=5
```

The variable and the `subPath` file are finally up to date. Remember the rule:

| Where the setting arrives | After a change to the ConfigMap |
|---|---|
| Environment variable | nothing changes, until the restart |
| Mounted directory | updated by itself, with a delay |
| `subPath` file | nothing changes, until the restart |

## 📚 Exercise 7: a missing ConfigMap

What happens if a Pod asks for a ConfigMap that does not exist? Create a Pod
that expects `meteo-absent`:

```bash
cat <<'YAML' | kubectl apply -n essai-config -f -
apiVersion: v1
kind: Pod
metadata:
  name: sans-config
spec:
  containers:
    - name: sans-config
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "3600"]
      envFrom:
        - configMapRef:
            name: meteo-absent
YAML
sleep 8; kubectl get pod sans-config -n essai-config
```

```text
pod/sans-config created
NAME          READY   STATUS                       RESTARTS   AGE
sans-config   0/1     CreateContainerConfigError   0          8s
```

The container does not start: `CreateContainerConfigError`. The Pod events of
type `Warning` say why:

```bash
kubectl get events -n essai-config --field-selector involvedObject.name=sans-config,type=Warning -o custom-columns=RAISON:.reason,MESSAGE:.message
```

```text
RAISON   MESSAGE
Failed   Error: configmap "meteo-absent" not found
```

Hence the practical rule: create the ConfigMaps **before** the Pods that need
them.

## 🧹 Clean up

Delete the work file and the scratch namespace:

```bash
rm -f ~/station.conf; kubectl delete namespace essai-config
```

```text
namespace "essai-config" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-configurer-par-configmap
dsoxlab check k8s-configurer-par-configmap
```

```text
╭─ Result: k8s-configurer-par-configmap ─╮
│  0 / 100 pts                           │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests       │
╰────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: configure an application with two
ConfigMaps, then carry a change all the way to the container.

```bash
dsoxlab run k8s-configurer-par-configmap
dsoxlab challenge k8s-configurer-par-configmap
```
