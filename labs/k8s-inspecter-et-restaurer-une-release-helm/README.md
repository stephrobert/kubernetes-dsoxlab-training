# Inspect a failed Helm release and restore it

**Helm** installs an application from a **chart**, a package of configurable
manifests. Each installation is called a **release**, and each change to the
release creates a new **revision**. In this course, you look for a chart in a
repository, you install a release, you describe it, you fail an upgrade, you
find out why, you roll back, then you run the chart's tests.

You work with a trial release, `atelier`, in a scratch namespace,
`essai-helm`. The challenge is about another release, already failed in
another namespace: you will repair it on your own, at the end.

Related page: [The helm command](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/tools/helm/helm-command-reference/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-inspecter-et-restaurer-une-release-helm
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it, and the lab installed
Helm.

The outputs shown in this course were recorded on this machine on 19 November
2026, with Kubernetes v1.37.2 and Helm 4.3.2.

## 📚 Exercise 1: look for a chart

Check the Helm version and the declared chart repositories:

```bash
helm version --short; helm repo list
```

```text
v4.3.2+g8346aaa
NAME   	URL                                   
podinfo	https://stefanprodan.github.io/podinfo
```

The lab declared the `podinfo` repository. `helm search repo` looks for a chart
in the declared repositories, and shows its latest version:

```bash
helm search repo podinfo/podinfo
```

```text
NAME           	CHART VERSION	APP VERSION	DESCRIPTION                      
podinfo/podinfo	6.17.0       	6.17.0     	Podinfo Helm chart for Kubernetes
```

`CHART VERSION` is the version of the chart, `APP VERSION` the version of the
application it installs. `--versions` lists every published version, newest
first:

```bash
helm search repo podinfo/podinfo --versions | head -5
```

```text
NAME           	CHART VERSION	APP VERSION	DESCRIPTION                      
podinfo/podinfo	6.17.0       	6.17.0     	Podinfo Helm chart for Kubernetes
podinfo/podinfo	6.16.0       	6.16.0     	Podinfo Helm chart for Kubernetes
podinfo/podinfo	6.15.0       	6.15.0     	Podinfo Helm chart for Kubernetes
podinfo/podinfo	6.14.1       	6.14.1     	Podinfo Helm chart for Kubernetes
```

## 📚 Exercise 2: install a release

Create the scratch namespace, then install the `atelier` release with version
6.16.0 of the chart. `--wait` waits until the application is ready, and `head`
shortens the output:

```bash
kubectl create namespace essai-helm
helm install atelier podinfo/podinfo --version 6.16.0 -n essai-helm --wait --timeout 180s | head -7
```

```text
namespace/essai-helm created
NAME: atelier
LAST DEPLOYED: Thu Nov 19 19:45:23 2026
NAMESPACE: essai-helm
STATUS: deployed
REVISION: 1
DESCRIPTION: Install complete
NOTES:
```

`helm list` shows the releases of a namespace:

```bash
helm list -n essai-helm
```

```text
NAME   	NAMESPACE 	REVISION	UPDATED                                	STATUS  	CHART         	APP VERSION
atelier	essai-helm	1       	2026-11-19 19:45:23.128326202 +0000 UTC	deployed	podinfo-6.16.0	6.16.0     
```

Revision 1, status `deployed`: the release is installed and works.

## 📚 Exercise 3: describe a release

`helm status` gives the state of the release:

```bash
helm status atelier -n essai-helm | head -7
```

```text
NAME: atelier
LAST DEPLOYED: Thu Nov 19 19:45:23 2026
NAMESPACE: essai-helm
STATUS: deployed
REVISION: 1
DESCRIPTION: Install complete
RESOURCES:
```

`helm get` reads what the release holds. `helm get values` shows the values
you passed to the chart:

```bash
helm get values atelier -n essai-helm
```

```text
USER-SUPPLIED VALUES:
null
```

`null`: none, the chart uses its default values. `helm get manifest` shows the
manifests Helm sent to the cluster. `grep` keeps only their type:

```bash
helm get manifest atelier -n essai-helm | grep -E '^kind:'
```

```text
kind: Service
kind: Deployment
```

## 📚 Exercise 4: an upgrade that fails

Move the release to version 6.17.0 of the chart, asking by mistake for 500 GiB
of memory for the container (`--set` changes a value of the chart):

```bash
helm upgrade atelier podinfo/podinfo --version 6.17.0 -n essai-helm --set resources.requests.memory=500Gi --wait --timeout 45s
```

```text
level=WARN msg="upgrade failed" name=atelier error="resource Deployment/essai-helm/atelier-podinfo not ready. status: InProgress, message: Available: 0/1\ncontext deadline exceeded"
Error: UPGRADE FAILED: resource Deployment/essai-helm/atelier-podinfo not ready. status: InProgress, message: Available: 0/1
context deadline exceeded
```

After 45 seconds, the Deployment is still not ready: Helm declares the failure.
`helm history` lists every revision, with its status:

```bash
helm history atelier -n essai-helm
```

```text
REVISION	UPDATED                 	STATUS  	CHART         	APP VERSION	DESCRIPTION                                                                                                                    
1       	Thu Nov 19 19:45:23 2026	deployed	podinfo-6.16.0	6.16.0     	Install complete                                                                                                               
2       	Thu Nov 19 19:45:26 2026	failed  	podinfo-6.17.0	6.17.0     	Upgrade "atelier" failed: resource Deployment/essai-helm/atelier-podinfo not ready. status: InProgress, message: Available: ...
```

Revision 2 has failed (`failed`). `helm status` now describes that revision:

```bash
helm status atelier -n essai-helm | head -7
```

```text
NAME: atelier
LAST DEPLOYED: Thu Nov 19 19:45:26 2026
NAMESPACE: essai-helm
STATUS: failed
REVISION: 2
DESCRIPTION: Upgrade "atelier" failed: resource Deployment/essai-helm/atelier-podinfo not ready. status: InProgress, message: Available: 0/1
context deadline exceeded
```

## 📚 Exercise 5: understand the failure

`--revision` reads a given revision. Here are the values of revision 2:

```bash
helm get values atelier -n essai-helm --revision 2
```

```text
USER-SUPPLIED VALUES:
resources:
  requests:
    memory: 500Gi
```

That is the faulty change. Look at the Pods:

```bash
kubectl get pods -n essai-helm
```

```text
NAME                               READY   STATUS    RESTARTS   AGE
atelier-podinfo-74575b5dfb-7bg97   0/1     Pending   0          45s
```

A single Pod, waiting (`Pending`). The old Pod has already been stopped: the
application no longer answers at all. The events tell why the new Pod finds no
room:

```bash
kubectl get events -n essai-helm --field-selector reason=FailedScheduling -o custom-columns=MESSAGE:.message | tail -1
```

```text
0/2 nodes are available: 2 Insufficient memory. preemption: 0/2 nodes are available: 2 Preemption is not helpful for scheduling.
```

Neither of the two nodes has 500 GiB of memory.

## 📚 Exercise 6: roll back

The last healthy revision is 1. `helm rollback` goes back to it:

```bash
helm rollback atelier 1 -n essai-helm --wait --timeout 120s
```

```text
Rollback was a success! Happy Helming!
```

Read the history again:

```bash
helm history atelier -n essai-helm
```

```text
REVISION	UPDATED                 	STATUS    	CHART         	APP VERSION	DESCRIPTION                                                                                                                    
1       	Thu Nov 19 19:45:23 2026	superseded	podinfo-6.16.0	6.16.0     	Install complete                                                                                                               
2       	Thu Nov 19 19:45:26 2026	failed    	podinfo-6.17.0	6.17.0     	Upgrade "atelier" failed: resource Deployment/essai-helm/atelier-podinfo not ready. status: InProgress, message: Available: ...
3       	Thu Nov 19 19:46:11 2026	deployed  	podinfo-6.16.0	6.16.0     	Rollback to 1                                                                                                                  
```

The rollback erased nothing. It created a **revision 3**, a copy of revision 1
(`Rollback to 1`). Revision 1 is now `superseded` (replaced), and revision 2
keeps the record of the failure. The application runs again:

```bash
kubectl get pods -n essai-helm
```

```text
NAME                               READY   STATUS    RESTARTS   AGE
atelier-podinfo-848f58c586-25wg9   1/1     Running   0          3s
```

## 📚 Exercise 7: run the chart's tests

A chart can ship tests: Pods that check that the application answers.
`helm test` runs them on the current revision:

```bash
helm test atelier -n essai-helm
```

```text
NAME: atelier
LAST DEPLOYED: Thu Nov 19 19:46:11 2026
NAMESPACE: essai-helm
STATUS: deployed
REVISION: 3
DESCRIPTION: Rollback to 1
TEST SUITE:     atelier-podinfo-grpc-test-9y20y
Last Started:   Thu Nov 19 19:46:14 2026
Last Completed: Thu Nov 19 19:46:19 2026
Phase:          Succeeded
TEST SUITE:     atelier-podinfo-jwt-test-hltiu
Last Started:   Thu Nov 19 19:46:19 2026
Last Completed: Thu Nov 19 19:46:24 2026
Phase:          Succeeded
TEST SUITE:     atelier-podinfo-service-test-y13sp
Last Started:   Thu Nov 19 19:46:24 2026
Last Completed: Thu Nov 19 19:46:29 2026
Phase:          Succeeded
```

Three tests, all successful (`Succeeded`), on revision 3. Their result stays
attached to the release: `helm status` still shows it afterwards. `sed` shows
the output from the first `TEST SUITE` on:

```bash
helm status atelier -n essai-helm | sed -n '/TEST SUITE/,/^$/p'
```

```text
TEST SUITE:     atelier-podinfo-grpc-test-9y20y
Last Started:   Thu Nov 19 19:46:14 2026
Last Completed: Thu Nov 19 19:46:19 2026
Phase:          Succeeded
TEST SUITE:     atelier-podinfo-jwt-test-hltiu
Last Started:   Thu Nov 19 19:46:19 2026
Last Completed: Thu Nov 19 19:46:24 2026
Phase:          Succeeded
TEST SUITE:     atelier-podinfo-service-test-y13sp
Last Started:   Thu Nov 19 19:46:24 2026
Last Completed: Thu Nov 19 19:46:29 2026
Phase:          Succeeded
NOTES:
1. Get the application URL by running these commands:
  echo "Visit http://127.0.0.1:8080 to use your application"
  kubectl -n essai-helm port-forward deploy/atelier-podinfo 8080:9898
```

## 🧹 Clean up

Uninstall the trial release, then delete its namespace:

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
namespace. Record the latest version of the chart and the faulty revision, go
back to the last healthy revision, then run the tests.

```bash
dsoxlab run k8s-inspecter-et-restaurer-une-release-helm
dsoxlab challenge k8s-inspecter-et-restaurer-une-release-helm
```
