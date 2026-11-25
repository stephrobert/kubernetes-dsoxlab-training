# Cap a namespace without blocking those who forget to declare themselves

The lesson shows the ResourceQuota, which caps what a namespace consumes, and
the LimitRange, which bounds and completes each container's resources. This
course adds cases the lesson does not show: a quota set while the namespace
already exceeds it, a blocked Deployment whose error hides elsewhere, a bound
on the gap between request and limit, a quota that only counts one kind of
Pod, and a quota on the number of objects.

You work in a scratch namespace, `essai-quota`, with `plafond-*` ("cap")
quotas and a `bornes-ecart` ("gap bounds") LimitRange. The challenge is about
another namespace: you will do it on your own, at the end.

Related page: [ResourceQuota and LimitRange](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/resource-quotas/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-resourcequota-limitrange
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

## ⏰ Exercise 1: a quota set after the fact

Create the namespace and three Pods, each requesting 100m of CPU:

```bash
kubectl create namespace essai-quota; kubectl run avant-1 --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-quota --overrides='{"spec":{"containers":[{"name":"avant-1","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"resources":{"requests":{"cpu":"100m"},"limits":{"cpu":"100m"}}}]}}' -- sleep 3600 >/dev/null; kubectl run avant-2 --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-quota --overrides='{"spec":{"containers":[{"name":"avant-2","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"resources":{"requests":{"cpu":"100m"},"limits":{"cpu":"100m"}}}]}}' -- sleep 3600 >/dev/null; kubectl run avant-3 --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-quota --overrides='{"spec":{"containers":[{"name":"avant-3","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"resources":{"requests":{"cpu":"100m"},"limits":{"cpu":"100m"}}}]}}' -- sleep 3600 >/dev/null; kubectl get pods -n essai-quota
```

```text
namespace/essai-quota created
NAME      READY   STATUS              RESTARTS   AGE
avant-1   0/1     ContainerCreating   0          0s
avant-2   0/1     ContainerCreating   0          0s
avant-3   0/1     ContainerCreating   0          0s
```

Now set a quota of two Pods, then count the Pods:

```bash
kubectl create quota plafond-pods --hard=pods=2 -n essai-quota; sleep 3; kubectl get quota plafond-pods -n essai-quota; kubectl get pods -n essai-quota --no-headers | wc -l
```

```text
resourcequota/plafond-pods created
NAME           REQUEST     LIMIT   AGE
plafond-pods   pods: 3/2           3s
3
```

The quota shows `3/2`: the namespace exceeds it, and the three Pods still
run. A quota deletes nothing. It only acts at creation. Try to create a
fourth one:

```bash
kubectl run apres --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-quota --overrides='{"spec":{"containers":[{"name":"apres","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"resources":{"requests":{"cpu":"100m"},"limits":{"cpu":"100m"}}}]}}' -- sleep 3600
```

```text
Error from server (Forbidden): pods "apres" is forbidden: exceeded quota: plafond-pods, requested: pods=1, used: pods=3, limited: pods=2
```

Refused, with the details of the calculation. Remove this quota:

```bash
kubectl delete quota plafond-pods -n essai-quota
```

```text
resourcequota "plafond-pods" deleted from essai-quota namespace
```

## 🕵️ Exercise 2: a blocked Deployment, the error is elsewhere

Set a 500m CPU quota, then create a three-replica Deployment requesting 200m
each. The command builds the Deployment, adds its resources with
`kubectl set resources --local`, then sends it:

```bash
kubectl create quota plafond-cpu --hard=requests.cpu=500m,limits.cpu=500m -n essai-quota; kubectl create deployment etal --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --replicas=3 -n essai-quota --dry-run=client -o yaml -- sleep 3600 | kubectl set resources --local -f - --requests=cpu=200m --limits=cpu=200m -o yaml | kubectl apply -f -; sleep 8; kubectl get deployment etal -n essai-quota; kubectl get quota plafond-cpu -n essai-quota
```

```text
resourcequota/plafond-cpu created
deployment.apps/etal created
NAME   READY   UP-TO-DATE   AVAILABLE   AGE
etal   1/3     1            1           8s
NAME          REQUEST                   LIMIT                   AGE
plafond-cpu   requests.cpu: 500m/500m   limits.cpu: 500m/500m   8s
```

`1/3`, without a word of error. The quota is full: the three `avant-*`
("before") Pods from exercise 1 count for 300m, and the Deployment's first Pod
for 200m. The Deployment does not create its Pods itself: its ReplicaSet does.
The error is therefore in the ReplicaSet's events:

```bash
kubectl describe replicaset -n essai-quota -l app=etal | grep FailedCreate | tail -1 | cut -c1-260
```

```text
  Warning  FailedCreate      8s (x4 over 8s)  replicaset-controller  (combined from similar events): Error creating: pods "etal-8bb4cbf65-b65d9" is forbidden: exceeded quota: plafond-cpu, requested: limits.cpu=200m,requests.cpu=200m, used: limits.cpu=500m,requ
```

When a Deployment does not reach its replica count without any Pod in error,
look at its ReplicaSet. Delete the Deployment, the Pods and the quota:

```bash
kubectl delete deployment etal -n essai-quota; kubectl delete pod --all -n essai-quota --wait=false >/dev/null; kubectl delete quota plafond-cpu -n essai-quota
```

```text
deployment.apps "etal" deleted from essai-quota namespace
resourcequota "plafond-cpu" deleted from essai-quota namespace
```

## 📐 Exercise 3: bound the gap between request and limit

`maxLimitRequestRatio` sets the maximum gap between a container's limit and
request. With 2, the limit cannot exceed twice the request. Create this
LimitRange, then two Pods: one requests 100m with a 200m limit, the other
requests 100m with a 500m limit (`cree` means "created").

```bash
cat <<'YAML' | kubectl apply -n essai-quota -f -
apiVersion: v1
kind: LimitRange
metadata:
  name: bornes-ecart
spec:
  limits:
    - type: Container
      maxLimitRequestRatio:
        cpu: "2"
YAML
```

```text
kubectl run raisonnable --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-quota --overrides='{"spec":{"containers":[{"name":"raisonnable","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"resources":{"requests":{"cpu":"100m"},"limits":{"cpu":"200m"}}}]}}' -- sleep 3600 >/dev/null; echo raisonnable cree; kubectl run gourmand --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-quota --overrides='{"spec":{"containers":[{"name":"gourmand","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"resources":{"requests":{"cpu":"100m"},"limits":{"cpu":"500m"}}}]}}' -- sleep 3600
limitrange/bornes-ecart created
raisonnable cree
Error from server (Forbidden): pods "gourmand" is forbidden: cpu max limit to request ratio per Container is 2, but provided ratio is 5.000000
```

The first one goes through, the second is refused with a ratio of 5. This
bound stops a container from reserving little and consuming a lot, at the
expense of its neighbours on the node. Remove the LimitRange:

```bash
kubectl delete limitrange bornes-ecart -n essai-quota
```

```text
limitrange "bornes-ecart" deleted from essai-quota namespace
```

## 🎯 Exercise 4: a quota that only counts Pods without resources

A quota can have a scope (`scopes`). With `BestEffort`, it only counts Pods
that declare no resource. Limit these Pods to one, then create two:

```bash
cat <<'YAML' | kubectl apply -n essai-quota -f -
apiVersion: v1
kind: ResourceQuota
metadata:
  name: plafond-besteffort
spec:
  hard:
    pods: "1"
  scopes: [BestEffort]
YAML
```

```text
kubectl run nu-1 --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-quota -- sleep 3600 >/dev/null; echo nu-1 cree; kubectl run nu-2 --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-quota -- sleep 3600
resourcequota/plafond-besteffort created
nu-1 cree
Error from server (Forbidden): pods "nu-2" is forbidden: exceeded quota: plafond-besteffort, requested: pods=1, used: pods=1, limited: pods=1
```

The second one is refused. Now create a Pod that declares resources, and look
at each Pod's quality of service (QoS) class:

```bash
kubectl run vetu --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-quota --overrides='{"spec":{"containers":[{"name":"vetu","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"resources":{"requests":{"cpu":"50m"},"limits":{"cpu":"50m"}}}]}}' -- sleep 3600 >/dev/null; kubectl get quota plafond-besteffort -n essai-quota; kubectl get pods -n essai-quota -l run -o custom-columns=NOM:.metadata.name,QOS:.status.qosClass --no-headers
```

```text
NAME                 REQUEST     LIMIT   AGE
plafond-besteffort   pods: 1/1           0s
avant-1       Burstable
avant-2       Burstable
avant-3       Burstable
nu-1          BestEffort
raisonnable   Burstable
vetu          Burstable
```

`vetu` ("dressed") is accepted, and the quota stays at `1/1`: it does not
count it. Only `nu-1` ("bare") is `BestEffort`. This scope lets through the
applications that declare themselves, and caps the ones that say nothing.

## 🔢 Exercise 5: count objects

`count/<resource>` caps a number of objects. Limit ConfigMaps to two, and
look at what the quota already counts:

```bash
kubectl create quota plafond-objets --hard=count/configmaps=2 -n essai-quota; sleep 3; kubectl get quota plafond-objets -n essai-quota; kubectl get configmaps -n essai-quota
```

```text
resourcequota/plafond-objets created
NAME             REQUEST                 LIMIT   AGE
plafond-objets   count/configmaps: 1/2           3s
NAME               DATA   AGE
kube-root-ca.crt   1      16s
```

`1/2` in a namespace where you created no ConfigMap: every namespace
automatically gets `kube-root-ca.crt`, the API's certificate. Create two
ConfigMaps:

```bash
kubectl create configmap reglages-1 -n essai-quota --from-literal=a=1 >/dev/null; echo reglages-1 cree; kubectl create configmap reglages-2 -n essai-quota --from-literal=a=2
```

```text
reglages-1 cree
error: failed to create configmap: configmaps "reglages-2" is forbidden: exceeded quota: plafond-objets, requested: count/configmaps=1, used: count/configmaps=2, limited: count/configmaps=2
```

The second one is refused. For an object quota, also count the ones the
cluster creates itself.

## 🧹 Clean-up

Delete the scratch namespace. The quotas, Pods and ConfigMaps go with it:

```bash
kubectl delete namespace essai-quota
```

```text
namespace "essai-quota" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-resourcequota-limitrange
dsoxlab check cka-resourcequota-limitrange
```

```text
╭─ Result: cka-resourcequota-limitrange ─╮
│  0 / 100 pts                           │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests       │
╰────────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a namespace to cap, without blocking the
Pods that forget to declare their resources.

```bash
dsoxlab run cka-resourcequota-limitrange
dsoxlab challenge cka-resourcequota-limitrange
```
