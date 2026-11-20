# Install, upgrade and roll back with Helm 4

A Helm **chart** is a directory: manifest templates, and a **values** file that
fills them. In this course, you create a chart, check it, install it and
change its values. Then you go back in three ways: to a given revision,
without a number, and after an uninstall. You will also see `upgrade
--install`, which installs or upgrades depending on whether the release
exists.

You work with a trial chart, `bonjour`, in a scratch namespace,
`essai-chart`. The challenge is about another chart, already prepared: you
will do it on your own, at the end.

Related page: [Install and manage Helm releases](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/tools/helm/helm-install-releases/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-helm-install-upgrade
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it, and the lab installed
Helm.

The outputs shown in this course were recorded on this machine on 20 November
2026, with Kubernetes v1.37.2 and Helm 4.3.2.

## 📚 Exercise 1: create a chart

`helm create` creates a complete sample chart. Create it in a work directory:

```bash
mkdir -p ~/essai-charts && cd ~/essai-charts && helm create bonjour
```

```text
Creating bonjour
```

Here are its files:

```bash
cd ~/essai-charts && find bonjour -type f | sort
```

```text
bonjour/.helmignore
bonjour/Chart.yaml
bonjour/templates/NOTES.txt
bonjour/templates/_helpers.tpl
bonjour/templates/deployment.yaml
bonjour/templates/hpa.yaml
bonjour/templates/httproute.yaml
bonjour/templates/ingress.yaml
bonjour/templates/service.yaml
bonjour/templates/serviceaccount.yaml
bonjour/templates/tests/test-connection.yaml
bonjour/values.yaml
```

Three things matter:

- `Chart.yaml` describes the chart (its name, its version);
- `values.yaml` holds the default values;
- `templates/` holds the manifest templates, which Helm fills with the values.

## 📚 Exercise 2: the values of a chart

Read the identity of the chart:

```bash
grep -E '^(name|version|appVersion):' ~/essai-charts/bonjour/Chart.yaml
```

```text
name: bonjour
version: 0.1.0
appVersion: "1.16.0"
```

`version` is the version of the chart. `appVersion` is the version of the
application it is meant to install. Now read a few default values:

```bash
grep -n -E '^replicaCount|^image:|^  repository:|^  tag:' ~/essai-charts/bonjour/values.yaml
```

```text
6:replicaCount: 1
9:image:
10:  repository: nginx
14:  tag: ""
```

1 replica, image `nginx`, empty tag. The Deployment template shows how these
values are used:

```bash
grep -n 'image:' ~/essai-charts/bonjour/templates/deployment.yaml
```

```text
41:          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
```

Helm replaces the `{{ }}`. If `image.tag` is empty, Helm takes `appVersion`
instead: the image would be `nginx:1.16.0`, a very old version. Give the tag a
recent version, with its digest:

```bash
sed -i 's|^  tag: ""|  tag: "1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"|' ~/essai-charts/bonjour/values.yaml; grep -n '^  tag:' ~/essai-charts/bonjour/values.yaml
```

```text
14:  tag: "1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
```

## 📚 Exercise 3: check before installing

`helm lint` looks for errors in a chart:

```bash
helm lint ~/essai-charts/bonjour
```

```text
==> Linting /home/ansible/essai-charts/bonjour
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

No error, just a suggestion (add an icon). `helm template` shows the produced
manifests, without installing anything. `grep` keeps only their type, the
number of replicas and the images:

```bash
helm template bonjour ~/essai-charts/bonjour | grep -E '^kind:|replicas:|image:'
```

```text
kind: ServiceAccount
kind: Service
kind: Deployment
  replicas: 1
          image: "nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
kind: Pod
      image: busybox
```

The Deployment does use your tag. The `Pod` at the end is the chart's test
(`templates/tests/`): only `helm test` will start it.

## 📚 Exercise 4: install from a directory

Create the scratch namespace, then install the chart from its directory, under
the release name `bonjour`:

```bash
kubectl create namespace essai-chart
helm install bonjour ~/essai-charts/bonjour -n essai-chart --wait --timeout 180s | head -6
kubectl get deployment -n essai-chart
```

```text
namespace/essai-chart created
NAME: bonjour
LAST DEPLOYED: Fri Nov 20 19:02:52 2026
NAMESPACE: essai-chart
STATUS: deployed
REVISION: 1
DESCRIPTION: Install complete
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
bonjour   1/1     1            1           1s
```

Revision 1, with 1 replica, the default value.

## 📚 Exercise 5: change a value

`--set` changes a value on the command line, without touching the file. Move
to 3 replicas:

```bash
helm upgrade bonjour ~/essai-charts/bonjour -n essai-chart --set replicaCount=3 --wait --timeout 180s | head -6
```

```text
Release "bonjour" has been upgraded. Happy Helming!
NAME: bonjour
LAST DEPLOYED: Fri Nov 20 19:02:53 2026
NAMESPACE: essai-chart
STATUS: deployed
REVISION: 2
```

`helm get values` shows the values you passed:

```bash
helm get values bonjour -n essai-chart; kubectl get deployment -n essai-chart
```

```text
USER-SUPPLIED VALUES:
replicaCount: 3
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
bonjour   3/3     3            3           12s
```

## 📚 Exercise 6: an upgrade with another value

What happens to the values passed last time? First run an `upgrade` **with no
value at all**:

```bash
helm upgrade bonjour ~/essai-charts/bonjour -n essai-chart --wait --timeout 180s > /dev/null; helm get values bonjour -n essai-chart; kubectl get deployment -n essai-chart
```

```text
USER-SUPPLIED VALUES:
replicaCount: 3
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
bonjour   3/3     3            3           13s
```

With no value at all, Helm takes those of the previous revision: still 3
replicas. Now pass **another** value, an `equipe` ("team") label on the Pods:

```bash
helm upgrade bonjour ~/essai-charts/bonjour -n essai-chart --set podLabels.equipe=accueil --wait --timeout 180s > /dev/null; helm get values bonjour -n essai-chart; kubectl get deployment -n essai-chart
```

```text
USER-SUPPLIED VALUES:
podLabels:
  equipe: accueil
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
bonjour   1/1     1            1           15s
```

Back to 1 replica. As soon as you pass a value, Helm starts again from the
chart's default values, plus **only** those of this command: `replicaCount=3`
is lost. `--reuse-values` keeps the previous values and adds the new ones:

```bash
helm upgrade bonjour ~/essai-charts/bonjour -n essai-chart --reuse-values --set replicaCount=3 --wait --timeout 180s > /dev/null; helm get values bonjour -n essai-chart; kubectl get deployment -n essai-chart
```

```text
USER-SUPPLIED VALUES:
podLabels:
  equipe: accueil
replicaCount: 3
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
bonjour   3/3     3            3           16s
```

Both values are there. Each `upgrade` created a revision:

```bash
helm history bonjour -n essai-chart
```

```text
REVISION	UPDATED                 	STATUS    	CHART        	APP VERSION	DESCRIPTION     
1       	Fri Nov 20 19:02:52 2026	superseded	bonjour-0.1.0	1.16.0     	Install complete
2       	Fri Nov 20 19:02:53 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
3       	Fri Nov 20 19:03:04 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
4       	Fri Nov 20 19:03:05 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
5       	Fri Nov 20 19:03:07 2026	deployed  	bonjour-0.1.0	1.16.0     	Upgrade complete
```

The `CHART` column gives the name and version of the chart each revision
used: here always `bonjour-0.1.0`, since `Chart.yaml` did not change. The
`APP VERSION` column shows `1.16.0`, the chart's `appVersion`, while the image
runs 1.30.5: this column copies `Chart.yaml`, it does not read the image.

## 📚 Exercise 7: go back to a revision

Go back to revision 2, the one with 3 replicas and no label:

```bash
helm rollback bonjour 2 -n essai-chart --wait --timeout 180s
```

```text
Rollback was a success! Happy Helming!
```

```bash
helm history bonjour -n essai-chart; helm get values bonjour -n essai-chart; kubectl get deployment -n essai-chart
```

```text
REVISION	UPDATED                 	STATUS    	CHART        	APP VERSION	DESCRIPTION     
1       	Fri Nov 20 19:02:52 2026	superseded	bonjour-0.1.0	1.16.0     	Install complete
2       	Fri Nov 20 19:02:53 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
3       	Fri Nov 20 19:03:04 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
4       	Fri Nov 20 19:03:05 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
5       	Fri Nov 20 19:03:07 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
6       	Fri Nov 20 19:03:09 2026	deployed  	bonjour-0.1.0	1.16.0     	Rollback to 2   
USER-SUPPLIED VALUES:
replicaCount: 3
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
bonjour   3/3     3            3           20s
```

A revision 6 appeared (`Rollback to 2`), with the values of revision 2:
3 replicas, no more label. Check that the application answers, on the
internal address of its Service (`grep -o` keeps only the page title):

```bash
IP=$(kubectl get service bonjour -n essai-chart -o jsonpath='{.spec.clusterIP}'); curl -s "http://$IP" | grep -o '<title>.*</title>'
```

```text
<title>Welcome to nginx!</title>
```

## 📚 Exercise 8: a rollback without a number

Do one more upgrade, to 2 replicas:

```bash
helm upgrade bonjour ~/essai-charts/bonjour -n essai-chart --reuse-values --set replicaCount=2 --wait --timeout 180s > /dev/null; helm history bonjour -n essai-chart
```

```text
REVISION	UPDATED                 	STATUS    	CHART        	APP VERSION	DESCRIPTION     
1       	Fri Nov 20 19:02:52 2026	superseded	bonjour-0.1.0	1.16.0     	Install complete
2       	Fri Nov 20 19:02:53 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
3       	Fri Nov 20 19:03:04 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
4       	Fri Nov 20 19:03:05 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
5       	Fri Nov 20 19:03:07 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
6       	Fri Nov 20 19:03:09 2026	superseded	bonjour-0.1.0	1.16.0     	Rollback to 2   
7       	Fri Nov 20 19:03:12 2026	deployed  	bonjour-0.1.0	1.16.0     	Upgrade complete
```

Without a number, `helm rollback` goes back to the revision before the
current one:

```bash
helm rollback bonjour -n essai-chart --wait --timeout 180s
```

```text
Rollback was a success! Happy Helming!
```

```bash
helm history bonjour -n essai-chart; helm get values bonjour -n essai-chart
```

```text
REVISION	UPDATED                 	STATUS    	CHART        	APP VERSION	DESCRIPTION     
1       	Fri Nov 20 19:02:52 2026	superseded	bonjour-0.1.0	1.16.0     	Install complete
2       	Fri Nov 20 19:02:53 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
3       	Fri Nov 20 19:03:04 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
4       	Fri Nov 20 19:03:05 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
5       	Fri Nov 20 19:03:07 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
6       	Fri Nov 20 19:03:09 2026	superseded	bonjour-0.1.0	1.16.0     	Rollback to 2   
7       	Fri Nov 20 19:03:12 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
8       	Fri Nov 20 19:03:12 2026	deployed  	bonjour-0.1.0	1.16.0     	Rollback to 6   
USER-SUPPLIED VALUES:
replicaCount: 3
```

Revision 8 says `Rollback to 6`: the previous revision was the rollback of
exercise 7, not revision 1 or 2. Without a number, Helm goes back one step
only, whatever that step holds. To target a given revision, give its number.

## 📚 Exercise 9: upgrade --install, twice

`helm install` fails if the release already exists (`cannot reuse a name that
is still in use`), and `helm upgrade` fails if it does not exist (`has no
deployed releases`). `helm upgrade --install` does one or the other: it is the
command you can run again without thinking, in a script or a pipeline. First
look at the releases of the namespace:

```bash
helm list -n essai-chart
```

```text
NAME   	NAMESPACE  	REVISION	UPDATED                                	STATUS  	CHART        	APP VERSION
bonjour	essai-chart	8       	2026-11-20 19:03:12.748038061 +0000 UTC	deployed	bonjour-0.1.0	1.16.0     
```

Run `upgrade --install` for a release `salut` that does not exist:

```bash
helm upgrade --install salut ~/essai-charts/bonjour -n essai-chart --wait --timeout 180s | head -6
```

```text
Release "salut" does not exist. Installing it now.
NAME: salut
LAST DEPLOYED: Fri Nov 20 19:03:14 2026
NAMESPACE: essai-chart
STATUS: deployed
REVISION: 1
```

Helm installed it. Run exactly the same command again:

```bash
helm upgrade --install salut ~/essai-charts/bonjour -n essai-chart --wait --timeout 180s | head -6
```

```text
Release "salut" has been upgraded. Happy Helming!
NAME: salut
LAST DEPLOYED: Fri Nov 20 19:03:15 2026
NAMESPACE: essai-chart
STATUS: deployed
REVISION: 2
```

This time it is an upgrade. The history shows both:

```bash
helm history salut -n essai-chart
```

```text
REVISION	UPDATED                 	STATUS    	CHART        	APP VERSION	DESCRIPTION     
1       	Fri Nov 20 19:03:14 2026	superseded	bonjour-0.1.0	1.16.0     	Install complete
2       	Fri Nov 20 19:03:15 2026	deployed  	bonjour-0.1.0	1.16.0     	Upgrade complete
```

## 📚 Exercise 10: uninstall and keep the history

`helm uninstall` deletes the objects of the release and, by default, its
history. With `--keep-history`, the history stays:

```bash
helm uninstall salut -n essai-chart --keep-history --wait
```

```text
release "salut" uninstalled
```

```bash
helm list -n essai-chart; helm list -n essai-chart --uninstalled
```

```text
NAME   	NAMESPACE  	REVISION	UPDATED                                	STATUS     	CHART        	APP VERSION
bonjour	essai-chart	8       	2026-11-20 19:03:12.748038061 +0000 UTC	deployed   	bonjour-0.1.0	1.16.0     
salut  	essai-chart	2       	2026-11-20 19:03:15.885798202 +0000 UTC	uninstalled	bonjour-0.1.0	1.16.0     
NAME 	NAMESPACE  	REVISION	UPDATED                                	STATUS     	CHART        	APP VERSION
salut	essai-chart	2       	2026-11-20 19:03:15.885798202 +0000 UTC	uninstalled	bonjour-0.1.0	1.16.0     
```

With Helm 4.3.2, `helm list` without an option also shows the uninstalled
release, with the `uninstalled` status. `--uninstalled` keeps only those. The
objects, though, are gone:

```bash
helm history salut -n essai-chart; kubectl get deployment -n essai-chart
```

```text
REVISION	UPDATED                 	STATUS     	CHART        	APP VERSION	DESCRIPTION            
1       	Fri Nov 20 19:03:14 2026	superseded 	bonjour-0.1.0	1.16.0     	Install complete       
2       	Fri Nov 20 19:03:15 2026	uninstalled	bonjour-0.1.0	1.16.0     	Uninstallation complete
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
bonjour   3/3     3            3           24s
```

No more `salut-bonjour` Deployment. The name stays taken as long as the
history exists, even for a `helm install`:

```bash
helm install salut ~/essai-charts/bonjour -n essai-chart 2>&1 | tail -1
```

```text
Error: INSTALLATION FAILED: release name check failed: cannot reuse a name that is still in use
```

A rollback, though, works: it recreates the objects from a kept revision.

```bash
helm rollback salut 1 -n essai-chart --wait --timeout 180s
```

```text
Rollback was a success! Happy Helming!
```

```bash
helm history salut -n essai-chart; kubectl get deployment -n essai-chart
```

```text
REVISION	UPDATED                 	STATUS     	CHART        	APP VERSION	DESCRIPTION            
1       	Fri Nov 20 19:03:14 2026	superseded 	bonjour-0.1.0	1.16.0     	Install complete       
2       	Fri Nov 20 19:03:15 2026	uninstalled	bonjour-0.1.0	1.16.0     	Uninstallation complete
3       	Fri Nov 20 19:03:16 2026	deployed   	bonjour-0.1.0	1.16.0     	Rollback to 1          
NAME            READY   UP-TO-DATE   AVAILABLE   AGE
bonjour         3/3     3            3           25s
salut-bonjour   1/1     1            1           1s
```

Revision 3 takes back revision 1, and `salut-bonjour` is back. Without
`--keep-history`, there would be nothing left to take back.

## 🧹 Clean up

Uninstall both releases, delete the namespace and the trial chart:

```bash
helm uninstall bonjour salut -n essai-chart --wait; kubectl delete namespace essai-chart; rm -rf ~/essai-charts
```

```text
release "bonjour" uninstalled
release "salut" uninstalled
namespace "essai-chart" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset ckad-helm-install-upgrade
dsoxlab check ckad-helm-install-upgrade
```

```text
╭─ Result: ckad-helm-install-upgrade ─╮
│  0 / 100 pts                        │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests    │
╰─────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: another chart, already prepared. Install it,
raise its version, upgrade the release with new values, then go back to its
first revision.

```bash
dsoxlab run ckad-helm-install-upgrade
dsoxlab challenge ckad-helm-install-upgrade
```
