# Drain a worker for maintenance, without cutting the service

The lesson shows how to prepare a maintenance: `cordon`, `drain`, and a
PodDisruptionBudget that protects the application. This course looks at what
happens under `drain` and adds cases the lesson does not show: an eviction
requested by hand from the API, the refusal of a budget already used up, and
a server-side dry-run drain that waits for the budget to let it through.

You work in a scratch namespace, `essai-maintenance`, with a `comptoir`
("counter") Deployment and its `comptoir-pdb` budget. No node is really
drained. The challenge is about other objects: you will do it on your own, at
the end.

Related page (in French): [Préparer une maintenance de cluster Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/preparer-maintenance-cluster-kubernetes/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-node-drain-cordon
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

Create the namespace, a three-replica Deployment and a budget that tolerates
a single unavailable Pod at a time. The readiness probe waits 20 seconds: a
replaced Pod therefore takes a while to be ready again, which leaves time to
watch the budget.

```bash
kubectl create namespace essai-maintenance; kubectl create deployment comptoir --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb --replicas=3 -n essai-maintenance >/dev/null; kubectl patch deployment comptoir -n essai-maintenance --type=json -p '[{"op":"add","path":"/spec/template/spec/containers/0/readinessProbe","value":{"httpGet":{"port":80},"initialDelaySeconds":20}}]' >/dev/null; kubectl rollout status deployment/comptoir -n essai-maintenance --timeout=120s >/dev/null; kubectl create poddisruptionbudget comptoir-pdb -n essai-maintenance --selector=app=comptoir --max-unavailable=1; sleep 3; kubectl get pdb comptoir-pdb -n essai-maintenance
```

```text
namespace/essai-maintenance created
poddisruptionbudget.policy/comptoir-pdb created
NAME           MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS   AGE
comptoir-pdb   N/A             1                 1                     3s
```

`ALLOWED DISRUPTIONS` is 1: the budget accepts one disruption.

## 📨 Exercise 1: request an eviction by hand

`kubectl drain` does not delete Pods: it asks the API to evict them, one Pod
at a time, by sending an `Eviction` object. Do it yourself for a `comptoir`
Pod, then read the budget again:

```bash
P=$(kubectl get pods -n essai-maintenance -l app=comptoir -o jsonpath='{.items[0].metadata.name}'); printf '{"apiVersion":"policy/v1","kind":"Eviction","metadata":{"name":"%s","namespace":"essai-maintenance"}}' $P | kubectl create --raw /api/v1/namespaces/essai-maintenance/pods/$P/eviction -f - 2>&1 | cut -c1-200; echo; kubectl get pdb comptoir-pdb -n essai-maintenance
```

```text
{"kind":"Status","apiVersion":"v1","metadata":{},"status":"Success","code":201}

NAME           MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS   AGE
comptoir-pdb   N/A             1                 0                     3s
```

The API accepted (code 201) and the Pod left. The Deployment creates another
one, but it is not ready yet: the budget no longer allows any disruption.

## 🚫 Exercise 2: the budget refuses the next one

Right away, request the eviction of a second Pod:

```bash
P=$(kubectl get pods -n essai-maintenance -l app=comptoir --field-selector status.phase=Running -o jsonpath='{.items[1].metadata.name}'); printf '{"apiVersion":"policy/v1","kind":"Eviction","metadata":{"name":"%s","namespace":"essai-maintenance"}}' $P | kubectl create --raw /api/v1/namespaces/essai-maintenance/pods/$P/eviction -f - 2>&1 | cut -c1-200
```

```text
Error from server (TooManyRequests): Cannot evict pod as it would violate the pod's disruption budget.
```

Refused with HTTP code 429 (`TooManyRequests`): evicting this Pod would leave
two Pods unavailable. Nothing was deleted. Wait for the replacement to be
ready, then try again:

```bash
kubectl rollout status deployment/comptoir -n essai-maintenance --timeout=120s >/dev/null; sleep 3; kubectl get pdb comptoir-pdb -n essai-maintenance; P=$(kubectl get pods -n essai-maintenance -l app=comptoir -o jsonpath='{.items[0].metadata.name}'); printf '{"apiVersion":"policy/v1","kind":"Eviction","metadata":{"name":"%s","namespace":"essai-maintenance"}}' $P | kubectl create --raw /api/v1/namespaces/essai-maintenance/pods/$P/eviction -f - 2>&1 | cut -c1-200
```

```text
NAME           MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS   AGE
comptoir-pdb   N/A             1                 1                     28s
{"kind":"Status","apiVersion":"v1","metadata":{},"status":"Success","code":201}
```

The budget allows one disruption again, and the eviction goes through. This
is exactly what `drain` does on a node: it retries as long as the budget
refuses.

## 🧪 Exercise 3: a dry-run drain, played by the server

`--dry-run=server` sends the real eviction requests to the API, which checks
them without running anything. Unlike `--dry-run=client`, budgets are really
consulted. Simulate draining the control plane, right after exercise 2,
while the last replacement is not ready yet:

```bash
kubectl drain k8s-cp.lab --dry-run=server --ignore-daemonsets --delete-emptydir-data 2>&1 | tail -6 | cut -c1-160
```

```text
evicting pod essai-maintenance/comptoir-5478b99cd8-sz2jr (server dry run)
error when evicting pods/"comptoir-5478b99cd8-sz2jr" -n "essai-maintenance" (will retry after 5s): Cannot evict pod as it would violate the pod's disruption bud
evicting pod essai-maintenance/comptoir-5478b99cd8-sz2jr (server dry run)
error when evicting pods/"comptoir-5478b99cd8-sz2jr" -n "essai-maintenance" (will retry after 5s): Cannot evict pod as it would violate the pod's disruption bud
evicting pod essai-maintenance/comptoir-5478b99cd8-sz2jr (server dry run)
node/k8s-cp.lab drained (server dry run)
```

A `comptoir` Pod was running here on the control plane. The budget first
refuses to evict it, and `drain` retries every 5 seconds, until the
replacement is ready. If you run the command more than 20 seconds after
exercise 2, or if no `comptoir` Pod runs on this node, you will see no
refusal. On a real drain, these lines explain a drain that never ends. Check
that the node was not touched
(`ordonnançable` means "schedulable"):

```bash
kubectl get node k8s-cp.lab -o jsonpath='ordonnançable={.spec.unschedulable}{"\n"}'
```

```text
ordonnançable=
```

Empty field: the node still accepts Pods. The dry-run drain did not apply
`cordon` either.

## 🧹 Clean-up

Delete the scratch namespace:

```bash
kubectl delete namespace essai-maintenance
```

```text
namespace "essai-maintenance" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-node-drain-cordon
dsoxlab check cka-node-drain-cordon
```

```text
╭── Result: cka-node-drain-cordon ──╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests  │
╰───────────────────────────────────╯
```

0 out of 5: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a worker to drain for maintenance without
cutting the service, then to put back in service.

```bash
dsoxlab run cka-node-drain-cordon
dsoxlab challenge cka-node-drain-cordon
```
