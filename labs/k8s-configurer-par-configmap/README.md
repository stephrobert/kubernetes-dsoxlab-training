# Configure an application with a ConfigMap

A good container image does not hold its settings: the same image serves in
test and in production, with different settings. Kubernetes keeps these
settings in a separate object, the **ConfigMap**, and gives them to the
container as **environment variables** or as **files** in a directory. The
lesson shows `envFrom`, a volume, and what is updated after a change. This
course goes further: give a variable a name other than its key, choose the
name of a mounted file, see what `optional: true` hides, and switch
configuration through a versioned ConfigMap.

You work in a scratch namespace, `essai-config`, with a `meteo` application.
The challenge will ask you to configure another application: you will do it on
your own, at the end.

Related page: [Kubernetes ConfigMaps](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/configmaps/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-configurer-par-configmap
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster
`boutique` is running there, and your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 20 November
2026.

## 📚 Exercise 1: two ConfigMaps

Create the scratch namespace and two ConfigMaps:

- `meteo-reglages`, with two values, whose keys are lowercase: `ville` and
  `unite`;
- `meteo-fichiers`, with two files, `station.conf` and `alertes.conf`. Each
  `--from-file` adds a file, and its name becomes the key.

```bash
kubectl create namespace essai-config
kubectl create configmap meteo-reglages --from-literal=ville=Lyon --from-literal=unite=celsius -n essai-config
printf 'station=lyon-bron\nfrequence=10\n' > ~/station.conf
printf 'seuil-vent=90\n' > ~/alertes.conf
kubectl create configmap meteo-fichiers --from-file=$HOME/station.conf --from-file=$HOME/alertes.conf -n essai-config
kubectl get configmap meteo-reglages meteo-fichiers -n essai-config
```

```text
namespace/essai-config created
configmap/meteo-reglages created
configmap/meteo-fichiers created
NAME             DATA   AGE
meteo-reglages   2      0s
meteo-fichiers   2      0s
```

The `DATA` column counts the keys: two in each ConfigMap.

## 📚 Exercise 2: a variable that does not bear the name of its key

The `meteo` application expects two variables, `METEO_VILLE` and
`METEO_UNITE`. The keys of the ConfigMap are called `ville` and `unite`. With
`envFrom`, each key becomes a variable **under its exact name**: you would get
`ville` and `unite`, which the application does not read.

The `env` field with `configMapKeyRef` gives the name of your choice: `name`
is the name of the variable, `configMapKeyRef` says which ConfigMap and which
key fill it. The same Deployment also mounts `meteo-fichiers`, which exercise
3 details. Write the manifest in a file, then apply it:

```bash
cat > ~/meteo.yaml <<'YAML'
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
          env:
            - name: METEO_VILLE
              valueFrom:
                configMapKeyRef:
                  name: meteo-reglages
                  key: ville
            - name: METEO_UNITE
              valueFrom:
                configMapKeyRef:
                  name: meteo-reglages
                  key: unite
          volumeMounts:
            - name: fichiers
              mountPath: /etc/meteo
            - name: fichiers
              mountPath: /etc/capteur.ini
              subPath: capteur.ini
      volumes:
        - name: fichiers
          configMap:
            name: meteo-fichiers
            items:
              - key: station.conf
                path: capteur.ini
YAML
kubectl apply -n essai-config -f ~/meteo.yaml
kubectl rollout status deployment/meteo -n essai-config --timeout=120s | tail -1
kubectl exec deploy/meteo -n essai-config -- env | grep -i -E 'ville|unite'
```

```text
deployment.apps/meteo created
deployment "meteo" successfully rolled out
METEO_VILLE=Lyon
METEO_UNITE=celsius
```

Both variables bear the name the application expects, and no `ville` or
`unite` variable exists: `configMapKeyRef` only creates the variables you
name.

## 📚 Exercise 3: choose the mounted files and their name

In the volume, the `items` field lists the keys to mount, and `path` gives the
name of the file. Here, only the `station.conf` key is mounted, under the name
`capteur.ini`. Look at the directory:

```bash
kubectl exec deploy/meteo -n essai-config -- ls /etc/meteo
kubectl exec deploy/meteo -n essai-config -- cat /etc/meteo/capteur.ini
```

```text
capteur.ini
station=lyon-bron
frequence=10
```

A single file, `capteur.ini`. `alertes.conf` is not mounted: with `items`, a
key missing from the list does not appear in the directory.

The Deployment also mounts this file a second time, on `/etc/capteur.ini`,
with `subPath`. `subPath` names a path **inside the volume**: since the volume
renamed the key, this path is `capteur.ini`, not `station.conf`.

## 📚 Exercise 4: change, then measure what follows

Set `unite` to `fahrenheit`, then change the frequency in `station.conf` and
replace `meteo-fichiers`. `--dry-run=client -o yaml` builds the new ConfigMap
without creating it, and `kubectl replace` replaces the old one. Both files
are given again: a replaced ConfigMap only keeps the keys you pass to it.

```bash
kubectl patch configmap meteo-reglages -n essai-config -p '{"data":{"unite":"fahrenheit"}}'
printf 'station=lyon-bron\nfrequence=5\n' > ~/station.conf
kubectl create configmap meteo-fichiers --from-file=$HOME/station.conf --from-file=$HOME/alertes.conf -n essai-config --dry-run=client -o yaml | kubectl replace -f -
```

```text
configmap/meteo-reglages patched
configmap/meteo-fichiers replaced
```

Measure how long the directory takes to update. The loop reads the file again
every 5 seconds, and stops after 36 tries, that is 3 minutes, even if nothing
changes:

```bash
debut=$SECONDS; for i in $(seq 1 36); do kubectl exec deploy/meteo -n essai-config -- grep -q frequence=5 /etc/meteo/capteur.ini 2>/dev/null && break; sleep 5; done; echo "attente : $((SECONDS - debut)) s"
```

```text
attente : 86 s
```

The directory updated **on its own**, here in 86 seconds: Kubernetes only
reads ConfigMaps again at regular intervals. Renaming through `items` does not
change this refresh. Now compare the three places:

```bash
kubectl exec deploy/meteo -n essai-config -- cat /etc/meteo/capteur.ini /etc/capteur.ini
kubectl exec deploy/meteo -n essai-config -- printenv METEO_UNITE
```

```text
station=lyon-bron
frequence=5
station=lyon-bron
frequence=10
celsius
```

The file of the directory says `frequence=5`. The one set by `subPath` still
says `frequence=10`, and the variable still says `celsius`. To give a chosen
name to a file **and** keep the update, use `items` rather than `subPath`.

## 📚 Exercise 5: a typo, with and without `optional`

Create a Pod whose variable targets `meteo-reglage`, without the final `s`:
this ConfigMap does not exist.

```bash
cat > ~/sans-config.yaml <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: sans-config
spec:
  terminationGracePeriodSeconds: 2
  containers:
    - name: sans-config
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sleep", "3600"]
      env:
        - name: METEO_UNITE
          valueFrom:
            configMapKeyRef:
              name: meteo-reglage
              key: unite
YAML
kubectl apply -n essai-config -f ~/sans-config.yaml
sleep 8; kubectl get pod sans-config -n essai-config
kubectl get pod sans-config -n essai-config -o jsonpath='{.status.containerStatuses[0].state.waiting.message}{"\n"}'
```

```text
pod/sans-config created
NAME          READY   STATUS                       RESTARTS   AGE
sans-config   0/1     CreateContainerConfigError   0          9s
configmap "meteo-reglage" not found
```

The container does not start, and the message names the missing ConfigMap.
The typo shows at once. Delete the Pod, add `optional: true` under
`key: unite`, then create it again:

```bash
kubectl delete pod sans-config -n essai-config
sed -i 's/key: unite/key: unite\n              optional: true/' ~/sans-config.yaml
grep -A4 configMapKeyRef ~/sans-config.yaml
kubectl apply -n essai-config -f ~/sans-config.yaml
kubectl wait --for=condition=Ready pod/sans-config -n essai-config --timeout=60s
kubectl exec sans-config -n essai-config -- sh -c 'echo METEO_UNITE=[$METEO_UNITE]'
```

```text
pod "sans-config" deleted from essai-config namespace
            configMapKeyRef:
              name: meteo-reglage
              key: unite
              optional: true
pod/sans-config created
pod/sans-config condition met
METEO_UNITE=[]
```

The Pod starts, and the variable does not exist: the brackets are empty. The
same typo no longer produces **any error**. `optional: true` suits a truly
optional setting. Elsewhere, it hides name mistakes.

## 📚 Exercise 6: switch configuration through a versioned ConfigMap

A ConfigMap with `immutable: true` refuses any change. To switch
configuration, you create a new version under another name, and point the
Deployment to it. Create `meteo-reglages-v2`, immutable, with the `kelvin`
unit:

```bash
cat > ~/meteo-v2.yaml <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: meteo-reglages-v2
data:
  ville: Lyon
  unite: kelvin
immutable: true
YAML
kubectl apply -n essai-config -f ~/meteo-v2.yaml
```

```text
configmap/meteo-reglages-v2 created
```

Point both variables of the Deployment to `meteo-reglages-v2`.
`kubectl patch --type=json` replaces one precise value, named by its path:
`env/0` is the first variable, `env/1` the second. The Pod template changes,
so the Deployment replaces its Pod by itself:

```bash
kubectl patch deployment meteo -n essai-config --type=json -p '[
  {"op": "replace", "path": "/spec/template/spec/containers/0/env/0/valueFrom/configMapKeyRef/name", "value": "meteo-reglages-v2"},
  {"op": "replace", "path": "/spec/template/spec/containers/0/env/1/valueFrom/configMapKeyRef/name", "value": "meteo-reglages-v2"}
]'
kubectl rollout status deployment/meteo -n essai-config --timeout=120s | tail -1
sleep 3; kubectl exec deploy/meteo -n essai-config -- printenv METEO_UNITE
```

```text
deployment.apps/meteo patched
deployment "meteo" successfully rolled out
kelvin
```

No need for `rollout restart`: switching ConfigMap changes the Deployment,
which replaces its Pods. Now go back to the previous version of the
Deployment:

```bash
kubectl rollout undo deployment/meteo -n essai-config
kubectl rollout status deployment/meteo -n essai-config --timeout=120s | tail -1
sleep 3; kubectl exec deploy/meteo -n essai-config -- printenv METEO_UNITE
```

```text
Warning: resource deployments/meteo was previously managed with 'kubectl apply'. Rolling back will not update the kubectl.kubernetes.io/last-applied-configuration annotation, which may cause unexpected behavior on future 'kubectl apply' operations. Consider using 'kubectl apply' with your previous configuration file instead.
deployment.apps/meteo rolled back
deployment "meteo" successfully rolled out
fahrenheit
```

The Deployment points to `meteo-reglages` again. But the earlier Pod saw
`celsius`, and the restored Pod sees `fahrenheit`: `meteo-reglages` was
changed in exercise 4. Rolling back restores the earlier Deployment, not the
earlier configuration. With versioned, immutable ConfigMaps, each version of
the Deployment finds exactly its own settings.

The warning says that `rollout undo` does not update the annotation that
`kubectl apply` relies on. If you ever apply `~/meteo.yaml` again, that file
is what counts.

## 🧹 Clean up

Delete the work files and the scratch namespace:

```bash
rm -f ~/station.conf ~/alertes.conf ~/meteo.yaml ~/sans-config.yaml ~/meteo-v2.yaml
kubectl delete namespace essai-config
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
