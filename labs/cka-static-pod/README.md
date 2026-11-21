# Place a static Pod on a worker, without going through the API

The lesson shows static Pods: the kubelet starts them from files placed on the
node, without going through the API, and the API only sees a reflection of
them, the mirror Pod. This course places its static Pods on the control
plane, and adds cases the lesson does not show: a deleted mirror that comes
back, an edited manifest that recreates the Pod, a namespace that does not
exist, and a static Pod that wants to mount a ConfigMap.

You work with scratch manifests: `sentinelle-statique`,
`essai-statique-absent` and `lecteur-config`. The challenge is about the
worker and another Pod: you will do it on your own, at the end.

Related page: [Troubleshoot a cluster](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/cluster-troubleshooting/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-static-pod
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it. The static Pods'
directory belongs to root: writes go through `sudo`.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

## 🪞 Exercise 1: a static Pod, and its mirror

The kubelet reads where its static Pods live in its configuration
(`staticPodPath`). Place a Pod there, then look for it in the API
(`répertoire surveillé` means "watched directory"):

```bash
echo "répertoire surveillé : /etc/kubernetes/manifests"; cat <<YAML | sudo tee /etc/kubernetes/manifests/sentinelle-statique.yaml >/dev/null
apiVersion: v1
kind: Pod
metadata:
  name: sentinelle-statique
  namespace: default
spec:
  containers:
    - name: c
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo version 1; sleep 3600"]

YAML
sleep 15; kubectl get pods -A | grep sentinelle
```

```text
répertoire surveillé : /etc/kubernetes/manifests
default           sentinelle-statique-k8s-cp.lab             1/1     Running   0             15s
```

The Pod shows up in the API as `sentinelle-statique-k8s-cp.lab`: the
manifest's name followed by the node's name. That is the mirror. Delete it:

```bash
kubectl delete pod sentinelle-statique-k8s-cp.lab -n default; sleep 10; kubectl get pods -A | grep sentinelle
```

```text
pod "sentinelle-statique-k8s-cp.lab" deleted from default namespace
default           sentinelle-statique-k8s-cp.lab             1/1     Running   0             10s
```

It comes back straight away (10 seconds old). The real Pod runs on the node,
and the kubelet recreates its mirror in the API. To delete a static Pod, you
must remove its file, not its mirror.

## ✏️ Exercise 2: editing the manifest recreates the Pod

Note the Pod's container, edit the manifest on the node, wait for a new
container to show up, then read the logs (`conteneur avant` means "container
before", `recréé en` "recreated in", `après` "after"):

```bash
C1=$(sudo crictl ps --name c -q --label io.kubernetes.pod.name=sentinelle-statique-k8s-cp.lab); echo "conteneur avant : ${C1:0:13}"; sudo sed -i 's/version 1/version 2/' /etc/kubernetes/manifests/sentinelle-statique.yaml; debut=$(date +%s); C2=; until [ -n "$C2" ] && [ "$C2" != "$C1" ]; do sleep 2; C2=$(sudo crictl ps --name c -q --label io.kubernetes.pod.name=sentinelle-statique-k8s-cp.lab); done; echo "recréé en $(( $(date +%s) - debut )) s"; sleep 3; echo "conteneur après : ${C2:0:13}"; kubectl logs sentinelle-statique-k8s-cp.lab -n default
```

```text
conteneur avant : 5f9f58bcda249
recréé en 39 s
conteneur après : 5a409db223569
version 2
```

A new container, which prints `version 2`. The kubelet saw the file change,
stopped the old Pod and started the new one. The 41 seconds come from the
stop: `sleep` ignores the stop signal, and the kubelet waits for the 30-second
grace period before killing it.

## 🚫 Exercise 3: a namespace that does not exist

Place a static Pod in a namespace nobody created, then look for it in the API
and on the node:

```bash
cat <<YAML | sudo tee /etc/kubernetes/manifests/essai-statique-absent.yaml >/dev/null
apiVersion: v1
kind: Pod
metadata:
  name: essai-statique-absent
  namespace: essai-inexistant
spec:
  containers:
    - name: c
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "sleep 3600"]

YAML
sleep 20; kubectl get pods -A | grep essai-statique-absent; echo "API : code $?"; sudo crictl pods --name essai-statique-absent
```

```text
API : code 1
POD ID              CREATED             STATE               NAME                NAMESPACE           ATTEMPT             RUNTIME
```

Nothing in the API, nothing on the node. The kubelet's log says why:

```bash
sudo journalctl -u kubelet --since '-1 min' --no-pager | grep 'essai-statique-absent' | grep -m1 'failed to setup network' | cut -c1-200
```

```text
Nov 21 06:17:14 k8s-cp.lab kubelet[1147438]: E1121 06:17:14.716005 1147438 kuberuntime_sandbox.go:74] "Failed to create sandbox for pod" err="rpc error: code = Unknown desc = failed to setup network f
```

The kubelet did try to create the Pod, but the CNI (Calico) could not set up
its network, for lack of a namespace. The Pod therefore exists nowhere, and
only the kubelet's log says so: for a static Pod missing from the API, that is
where to look.

## 📄 Exercise 4: a static Pod cannot read a ConfigMap

Place a static Pod that mounts a ConfigMap:

```bash
cat <<YAML | sudo tee /etc/kubernetes/manifests/lecteur-config.yaml >/dev/null
apiVersion: v1
kind: Pod
metadata:
  name: lecteur-config
  namespace: default
spec:
  containers:
    - name: c
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "sleep 3600"]
      volumeMounts: [{name: v, mountPath: /conf}]
  volumes:
    - {name: v, configMap: {name: kube-root-ca.crt}}
YAML
sleep 20; kubectl get pods -A | grep lecteur-config; echo "API : code $?"; sudo journalctl -u kubelet --since '-1 min' --no-pager | grep -m1 -i 'lecteur-config' | grep -o 'static pods may not.*' | cut -c1-160
```

```text
API : code 1
static pods may not reference configmaps"
```

Missing from the API, and the kubelet refuses the file: `static pods may not
reference configmaps`. A static Pod does not depend on the API, so it cannot
read what only exists in the API: no ConfigMap, no Secret, no ServiceAccount.
Its configuration comes from the node, through a `hostPath` volume.

## 🧹 Clean-up

Remove the three scratch manifests, wait for the kubelet to stop the Pods,
and check none is left in the API:

```bash
sudo rm -f /etc/kubernetes/manifests/sentinelle-statique.yaml /etc/kubernetes/manifests/essai-statique-absent.yaml /etc/kubernetes/manifests/lecteur-config.yaml; sleep 40; kubectl get pods -A | grep -c -E 'sentinelle|lecteur-config'
```

```text
0
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-static-pod
dsoxlab check cka-static-pod
```

```text
╭───── Result: cka-static-pod ──────╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests  │
╰───────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a static Pod to place on the worker, in the
directory its kubelet watches.

```bash
dsoxlab run cka-static-pod
dsoxlab challenge cka-static-pod
```
