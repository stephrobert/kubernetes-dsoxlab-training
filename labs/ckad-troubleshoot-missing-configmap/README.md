# A Pod blocked by a ConfigMap that does not exist

A Pod can wait for something before it even starts its container: a
ConfigMap, a Secret, a given key. If that something is missing, the Pod stays
blocked, and `kubectl logs` says nothing, since the container does not exist
yet. In this course, you block a Pod on a missing ConfigMap, you read the cause
in its events, you unblock it without creating it again, then you see three
variants: a missing key, an environment variable waiting for a ConfigMap, and
an optional ConfigMap.

You work in a scratch namespace, `essai-panne`, with the `accueil` ("home"),
`cle-absente` ("missing-key"), `variable` and `facultatif` ("optional") Pods.
The challenge is about another blocked Pod, in another namespace: you will fix
it on your own, at the end.

Related page: [Debug an application](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/debug-applications/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-troubleshoot-missing-configmap
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 20 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: a volume waiting for a missing ConfigMap

Create the scratch namespace and an nginx `accueil` Pod. Its home page comes
from a volume filled by the `reglages-site` ConfigMap, which does not exist:

```bash
kubectl create namespace essai-panne
cat <<'YAML' | kubectl apply -n essai-panne -f -
apiVersion: v1
kind: Pod
metadata:
  name: accueil
spec:
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
      volumeMounts:
        - name: reglages
          mountPath: /usr/share/nginx/html
  volumes:
    - name: reglages
      configMap:
        name: reglages-site
YAML
```

```text
namespace/essai-panne created
pod/accueil created
```

15 seconds later:

```bash
sleep 15; kubectl get pod accueil -n essai-panne
```

```text
NAME      READY   STATUS              RESTARTS   AGE
accueil   0/1     ContainerCreating   0          15s
```

`ContainerCreating` for 15 seconds. The logs?

```bash
kubectl logs accueil -n essai-panne 2>&1 | cut -c1-160
```

```text
Error from server (BadRequest): container "web" in pod "accueil" is waiting to start: ContainerCreating
```

No logs: the container does not exist yet. The cause is read in the Pod's
**events**, at the bottom of `kubectl describe`:

```bash
kubectl describe pod accueil -n essai-panne | sed -n '/^Events:/,$p' | cut -c1-170
```

```text
Events:
  Type     Reason       Age               From               Message
  ----     ------       ----              ----               -------
  Normal   Scheduled    15s               default-scheduler  Successfully assigned essai-panne/accueil to k8s-w1.lab
  Warning  FailedMount  7s (x5 over 15s)  kubelet            MountVolume.SetUp failed for volume "reglages" : configmap "reglages-site" not found
```

`FailedMount`: the kubelet cannot mount the `reglages` volume, because the
`reglages-site` ConfigMap does not exist. It has already tried 5 times. Note
the Pod's uid:

```bash
kubectl get pod accueil -n essai-panne -o jsonpath='uid={.metadata.uid}{"\n"}'
```

```text
uid=cf47334d-6359-4869-ad72-90c193dac868
```

## 📚 Exercise 2: the ConfigMap arrives, the Pod starts on its own

Create the expected ConfigMap. Its `index.html` key becomes the `index.html`
file of the volume ("welcome to the site"):

```bash
kubectl create configmap reglages-site -n essai-panne --from-literal=index.html='bienvenue sur le site'
```

```text
configmap/reglages-site created
```

Do not touch the Pod. Just wait until it is ready:

```bash
kubectl wait --for=condition=Ready pod/accueil -n essai-panne --timeout=180s; kubectl get pod accueil -n essai-panne -o jsonpath='uid={.metadata.uid}{"\n"}'; kubectl get pod accueil -n essai-panne
```

```text
pod/accueil condition met
uid=cf47334d-6359-4869-ad72-90c193dac868
NAME      READY   STATUS    RESTARTS   AGE
accueil   1/1     Running   0          16s
```

Same uid: the Pod was not created again. The kubelet retries the mount on its
own, and it succeeded as soon as the ConfigMap existed. The page is served:

```bash
IP=$(kubectl get pod accueil -n essai-panne -o jsonpath='{.status.podIP}'); curl -s "http://$IP/"
```

```text
bienvenue sur le site
```

## 📚 Exercise 3: a key that does not exist

The ConfigMap exists, but the `cle-absente` Pod asks for a given key,
`theme.css`, which it does not hold (`items` block):

```bash
cat <<'YAML' | kubectl apply -n essai-panne -f -
apiVersion: v1
kind: Pod
metadata:
  name: cle-absente
spec:
  containers:
    - name: web
      image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
      volumeMounts:
        - name: reglages
          mountPath: /config
  volumes:
    - name: reglages
      configMap:
        name: reglages-site
        items:
          - key: theme.css
            path: theme.css
YAML
```

```text
pod/cle-absente created
```

```bash
sleep 15; kubectl get pod cle-absente -n essai-panne; kubectl get events -n essai-panne --field-selector involvedObject.name=cle-absente,reason=FailedMount -o custom-columns=MESSAGE:.message --no-headers | sort -u | head -1 | cut -c1-170
```

```text
NAME          READY   STATUS              RESTARTS   AGE
cle-absente   0/1     ContainerCreating   0          15s
MountVolume.SetUp failed for volume "reglages" : configmap references non-existent config key: theme.css
```

Same blockage, another message: the ConfigMap is there, but the `theme.css`
key is missing. Always read the whole message: it is the one that tells what
to fix.

## 📚 Exercise 4: a variable waiting for a missing ConfigMap

The `variable` Pod reads a value from the missing `options-langue` ConfigMap
into an **environment variable** (`configMapKeyRef`) instead of a volume:

```bash
cat <<'YAML' | kubectl apply -n essai-panne -f -
apiVersion: v1
kind: Pod
metadata:
  name: variable
spec:
  containers:
    - name: app
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo langue=$LANGUE; sleep 3600"]
      env:
        - name: LANGUE
          valueFrom:
            configMapKeyRef:
              name: options-langue
              key: langue
YAML
```

```text
pod/variable created
```

```bash
sleep 10; kubectl get pod variable -n essai-panne; kubectl get events -n essai-panne --field-selector involvedObject.name=variable,reason=Failed -o custom-columns=MESSAGE:.message --no-headers | sort -u | head -1
```

```text
NAME       READY   STATUS                       RESTARTS   AGE
variable   0/1     CreateContainerConfigError   0          10s
Error: configmap "options-langue" not found
```

Another state: `CreateContainerConfigError`. The volume was mounted by the
kubelet before the container (`ContainerCreating`). The variable, on the other
hand, is used to prepare the container, and that preparation is what fails.
Two different states, one same cause: a missing ConfigMap.

## 📚 Exercise 5: an optional ConfigMap

`optional: true` tells Kubernetes that the ConfigMap may be missing, for the
variable as for the volume:

```bash
cat <<'YAML' | kubectl apply -n essai-panne -f -
apiVersion: v1
kind: Pod
metadata:
  name: facultatif
spec:
  containers:
    - name: app
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo langue=$LANGUE; ls /extra; sleep 3600"]
      env:
        - name: LANGUE
          valueFrom:
            configMapKeyRef:
              name: options-langue
              key: langue
              optional: true
      volumeMounts:
        - name: extra
          mountPath: /extra
  volumes:
    - name: extra
      configMap:
        name: options-langue
        optional: true
YAML
kubectl wait --for=condition=Ready pod/facultatif -n essai-panne --timeout=120s
```

```text
pod/facultatif created
pod/facultatif condition met
```

```bash
kubectl get pod facultatif -n essai-panne; kubectl logs facultatif -n essai-panne
```

```text
NAME         READY   STATUS    RESTARTS   AGE
facultatif   1/1     Running   0          0s
langue=
```

The Pod starts: the variable is empty, and the `/extra` directory is empty
(`ls` prints nothing). Keep `optional: true` for what can really be missing.
For a configuration the application needs, a blocked Pod is better than an
application that starts without it.

## 🧹 Clean up

Delete the scratch namespace, with its Pods and its ConfigMap:

```bash
kubectl delete namespace essai-panne
```

```text
namespace "essai-panne" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset ckad-troubleshoot-missing-configmap
dsoxlab check ckad-troubleshoot-missing-configmap
```

```text
╭─ Result: ckad-troubleshoot-missing-configmap ─╮
│  0 / 100 pts                                  │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests              │
╰───────────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: another Pod, blocked for an hour. Record the
cause from its events before fixing anything.

```bash
dsoxlab run ckad-troubleshoot-missing-configmap
dsoxlab challenge ckad-troubleshoot-missing-configmap
```
