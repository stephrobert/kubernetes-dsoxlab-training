# Inspect a failed Helm release and restore it

**Helm** installs an application from a **chart**, a package of configurable
manifests. Each installation is called a **release**, and each change to the
release creates a new **revision**. The lesson shows how to search for a
chart, install, describe, roll back and test. This course goes further:
filter the versions of a chart, see what a version changes, compare two
revisions, let Helm roll back on its own, and fall into the trap of a rollback
without a number.

You work with a scratch release, `atelier`, in a scratch namespace,
`essai-helm`. The challenge is about another release, already failed in
another namespace: you will repair it on your own, at the end.

Related page: [The helm command](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/tools/helm/helm-command-reference/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-inspecter-et-restaurer-une-release-helm
```

You are now connected to `k8s-cp.lab`, the node that drives the kubeadm
cluster (the control plane). Your kubectl already targets it, and the lab
installed Helm.

The outputs shown in this course were recorded on this machine on 20 November
2026, with Kubernetes v1.37.2 and Helm 4.3.2.

## 📚 Exercise 1: search, then filter the versions

Check the version of Helm and the declared chart repositories, then search for
the `podinfo` chart:

```bash
helm version --short; helm repo list
helm search repo podinfo/podinfo
```

```text
v4.3.2+g8346aaa
NAME   	URL
podinfo	https://stefanprodan.github.io/podinfo
NAME           	CHART VERSION	APP VERSION	DESCRIPTION
podinfo/podinfo	6.17.0       	6.17.0     	Podinfo Helm chart for Kubernetes
```

By default, `helm search repo` only shows the latest version of all.
`--versions` lists them, from the most recent to the oldest (`head` keeps the
first lines):

```bash
helm search repo podinfo/podinfo --versions | head -4
```

```text
NAME           	CHART VERSION	APP VERSION	DESCRIPTION
podinfo/podinfo	6.17.0       	6.17.0     	Podinfo Helm chart for Kubernetes
podinfo/podinfo	6.16.0       	6.16.0     	Podinfo Helm chart for Kubernetes
podinfo/podinfo	6.15.0       	6.15.0     	Podinfo Helm chart for Kubernetes
```

To stay on one series, for example the fixes of 6.12, give a **constraint** to
`--version`. `~6.12` means "6.12, with any fix":

```bash
helm search repo podinfo/podinfo --version '~6.12'
```

```text
NAME           	CHART VERSION	APP VERSION	DESCRIPTION
podinfo/podinfo	6.12.0       	6.12.0     	Podinfo Helm chart for Kubernetes
```

The search returns the latest version of this series, not the latest version
of all.

## 📚 Exercise 2: what a new version changes

Before upgrading, look at what the new version changes in the default values
of the chart. `helm show values` prints them, and `diff` compares both
outputs:

```bash
diff <(helm show values podinfo/podinfo --version 6.16.0) <(helm show values podinfo/podinfo --version 6.17.0); echo "code $?"
```

```text
11c11
<   tag: 6.16.0
---
>   tag: 6.17.0
98a99,103
>   # call the https backends with SPIFFE mTLS, presenting podinfo's SVID
>   backendMTLS: false
>   # the server SPIFFE IDs accepted from https backends, when empty any ID in podinfo's trust domain is accepted
>   # requires backendMTLS
>   backendIDs: []
code 1
```

The `<` lines come from 6.16.0, the `>` lines from 6.17.0. The tag of the
image changes, and 6.17.0 adds two settings, `backendMTLS` and `backendIDs`.

## 📚 Exercise 3: compare two revisions

Create the scratch namespace, install the `atelier` release in version 6.16.0,
then move it to 2 replicas. `head` and `sed` shorten the outputs:

```bash
kubectl create namespace essai-helm
helm install atelier podinfo/podinfo --version 6.16.0 -n essai-helm --wait --timeout 180s | head -7
helm upgrade atelier podinfo/podinfo --version 6.16.0 -n essai-helm --set replicaCount=2 --wait --timeout 180s | sed -n '4,6p'
```

```text
namespace/essai-helm created
NAME: atelier
LAST DEPLOYED: Fri Nov 20 18:30:38 2026
NAMESPACE: essai-helm
STATUS: deployed
REVISION: 1
DESCRIPTION: Install complete
NOTES:
NAMESPACE: essai-helm
STATUS: deployed
REVISION: 2
```

`helm get manifest --revision` gives the manifests a revision sent to the
cluster. Compare revisions 1 and 2:

```bash
diff <(helm get manifest atelier -n essai-helm --revision 1) <(helm get manifest atelier -n essai-helm --revision 2); echo "code $?"
```

```text
40c40
<   replicas: 1
---
>   replicas: 2
code 1
```

A single line differs. On a release that changed a lot, this comparison says
exactly what a revision brought.

## 📚 Exercise 4: a failure, and Helm rolls back on its own

Move the release to 6.17.0, asking by mistake for 500 GiB of memory for the
container. `--reuse-values` keeps the 2 replicas, and `--rollback-on-failure`
asks Helm to roll back on its own if the upgrade fails:

```bash
helm upgrade atelier podinfo/podinfo --version 6.17.0 -n essai-helm --reuse-values --set resources.requests.memory=500Gi --rollback-on-failure --timeout 45s; echo "code $?"
```

```text
level=WARN msg="upgrade failed" name=atelier error="resource Deployment/essai-helm/atelier-podinfo not ready. status: InProgress, message: Pending termination: 1\ncontext deadline exceeded"
Error: UPGRADE FAILED: release atelier failed, and has been rolled back due to rollback-on-failure being set: resource Deployment/essai-helm/atelier-podinfo not ready. status: InProgress, message: Pending termination: 1
context deadline exceeded
code 1
```

The upgrade failed, and Helm says so: `has been rolled back`. Look at the
history and the Pods:

```bash
helm history atelier -n essai-helm | cut -c1-120
kubectl get pods -n essai-helm
```

```text
REVISION	UPDATED                 	STATUS    	CHART         	APP VERSION	DESCRIPTION
1       	Fri Nov 20 18:30:38 2026	superseded	podinfo-6.16.0	6.16.0     	Install complete
2       	Fri Nov 20 18:30:40 2026	superseded	podinfo-6.16.0	6.16.0     	Upgrade complete
3       	Fri Nov 20 18:30:44 2026	failed    	podinfo-6.17.0	6.17.0     	Upgrade "atelier" failed: resource Deployment/es
4       	Fri Nov 20 18:31:29 2026	deployed  	podinfo-6.16.0	6.16.0     	Rollback to 2
NAME                               READY   STATUS    RESTARTS   AGE
atelier-podinfo-848f58c586-vcqvz   1/1     Running   0          53s
atelier-podinfo-848f58c586-zth98   1/1     Running   0          2s
```

Revision 3 failed, and Helm created revision 4, `Rollback to 2`. Both Pods run
again. Without this option, the release would stay failed, as the next
exercise shows.

## 📚 Exercise 5: two failures, then a rollback without a number

Run the same upgrade again, this time without `--rollback-on-failure`, and look
at the Pods:

```bash
helm upgrade atelier podinfo/podinfo --version 6.17.0 -n essai-helm --reuse-values --set resources.requests.memory=500Gi --wait --timeout 45s; echo "code $?"
kubectl get pods -n essai-helm
```

```text
level=WARN msg="upgrade failed" name=atelier error="resource Deployment/essai-helm/atelier-podinfo not ready. status: InProgress, message: Pending termination: 1\ncontext deadline exceeded"
Error: UPGRADE FAILED: resource Deployment/essai-helm/atelier-podinfo not ready. status: InProgress, message: Pending termination: 1
context deadline exceeded
code 1
NAME                               READY   STATUS    RESTARTS   AGE
atelier-podinfo-848f58c586-vcqvz   1/1     Running   0          98s
atelier-podinfo-86c7bcd589-8v9gz   0/1     Pending   0          45s
atelier-podinfo-86c7bcd589-fqc4x   0/1     Pending   0          45s
```

Both new Pods wait for room that does not exist (`Pending`), and a single old
Pod still serves: the application runs at half capacity. Why was one of the
two old Pods already stopped? The strategy of the Deployment says it:

```bash
kubectl get deployment atelier-podinfo -n essai-helm -o jsonpath='{.spec.strategy}{"\n"}'
```

```text
{"rollingUpdate":{"maxSurge":"25%","maxUnavailable":1},"type":"RollingUpdate"}
```

`maxUnavailable: 1`, set by the podinfo chart: during an update, one Pod may be
unavailable. Kubernetes stopped an old Pod without waiting for the new ones to
be ready. Now fail a second upgrade, with another wrong value, then read the
history again (`cut` trims long lines):

```bash
helm upgrade atelier podinfo/podinfo --version 6.17.0 -n essai-helm --reuse-values --set resources.requests.memory=400Gi --wait --timeout 45s 2>&1 | tail -1; helm history atelier -n essai-helm | cut -c1-120
```

```text
context deadline exceeded
REVISION	UPDATED                 	STATUS    	CHART         	APP VERSION	DESCRIPTION
1       	Fri Nov 20 18:30:38 2026	superseded	podinfo-6.16.0	6.16.0     	Install complete
2       	Fri Nov 20 18:30:40 2026	superseded	podinfo-6.16.0	6.16.0     	Upgrade complete
3       	Fri Nov 20 18:30:44 2026	failed    	podinfo-6.17.0	6.17.0     	Upgrade "atelier" failed: resource Deployment/es
4       	Fri Nov 20 18:31:29 2026	deployed  	podinfo-6.16.0	6.16.0     	Rollback to 2
5       	Fri Nov 20 18:31:31 2026	failed    	podinfo-6.17.0	6.17.0     	Upgrade "atelier" failed: resource Deployment/es
6       	Fri Nov 20 18:32:16 2026	failed    	podinfo-6.17.0	6.17.0     	Upgrade "atelier" failed: resource Deployment/es
```

Two failures in a row, revisions 5 and 6. Run a rollback **without a
number**:

```bash
helm rollback atelier -n essai-helm --wait --timeout 45s; echo "code $?"
helm history atelier -n essai-helm | cut -c1-120 | tail -2
```

```text
Error: release atelier failed: resource Deployment/essai-helm/atelier-podinfo not ready. status: InProgress, message: Pending termination: 1
context deadline exceeded
code 1
6       	Fri Nov 20 18:32:16 2026	failed    	podinfo-6.17.0	6.17.0     	Upgrade "atelier" failed: resource Deployment/es
7       	Fri Nov 20 18:33:01 2026	failed    	podinfo-6.17.0	6.17.0     	Release "atelier" failed: resource Deployment/es
```

The rollback failed as well. Without a number, `helm rollback` goes back to the
**previous** revision, whatever its status: here 5, itself failed. Revision 7
is therefore a copy of a failure.

## 📚 Exercise 6: go back to the right revision, then test

The last healthy revision is 2, with 2 replicas on 6.16.0. Give its number:

```bash
helm rollback atelier 2 -n essai-helm --wait --timeout 120s
helm history atelier -n essai-helm | cut -c1-120 | tail -1
kubectl get pods -n essai-helm
```

```text
Rollback was a success! Happy Helming!
8       	Fri Nov 20 18:33:47 2026	deployed  	podinfo-6.16.0	6.16.0     	Rollback to 2
NAME                               READY   STATUS    RESTARTS   AGE
atelier-podinfo-848f58c586-vcqvz   1/1     Running   0          3m11s
atelier-podinfo-848f58c586-zjsnm   1/1     Running   0          2s
```

Revision 8 is deployed, and both Pods run. Run the chart tests on this
revision. `sed` only keeps the revision and the result of each test:

```bash
helm test atelier -n essai-helm | sed -n '/^REVISION/p;/^DESCRIPTION/p;/Phase/p'
```

```text
REVISION: 8
DESCRIPTION: Rollback to 2
Phase:          Succeeded
Phase:          Succeeded
Phase:          Succeeded
```

Three tests succeeded, on revision 8.

## 🧹 Clean up

Uninstall the scratch release, then delete its namespace:

```bash
helm uninstall atelier -n essai-helm --wait; kubectl delete namespace essai-helm
```

```text
release "atelier" uninstalled
namespace "essai-helm" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-inspecter-et-restaurer-une-release-helm
dsoxlab check k8s-inspecter-et-restaurer-une-release-helm
```

```text
╭─ Result: k8s-inspecter-et-restaurer-une-release-helm ─╮
│  0 / 100 pts                                          │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests                      │
╰───────────────────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: another release, already failed in another
namespace. Record the latest version of a series of the chart and the faulty
revisions, go back to the last healthy revision, then run the tests.

```bash
dsoxlab run k8s-inspecter-et-restaurer-une-release-helm
dsoxlab challenge k8s-inspecter-et-restaurer-une-release-helm
```
