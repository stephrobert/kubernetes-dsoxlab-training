# Install, upgrade and roll back with Helm 4

A Helm **chart** is a directory: manifest templates, and a **values** file that
fills them. In this course, you create a chart, you read its values, you check
it before installing it, you install it, you change a value, you see what an
`upgrade` does with the values passed before, then you go back to a given
revision.

You work with a trial chart and release, `bonjour`, in a scratch namespace,
`essai-chart`. The challenge is about another chart, already prepared: you will
do it on your own, at the end.

Related page: [Install and manage Helm releases](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/tools/helm/helm-install-releases/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-helm-install-upgrade
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it, and the lab installed
Helm.

The outputs shown in this course were recorded on this machine on 19 November
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
LAST DEPLOYED: Thu Nov 19 19:52:13 2026
NAMESPACE: essai-chart
STATUS: deployed
REVISION: 1
DESCRIPTION: Install complete
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
bonjour   1/1     1            1           2s
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
LAST DEPLOYED: Thu Nov 19 19:52:15 2026
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
bonjour   3/3     3            3           4s
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
bonjour   3/3     3            3           4s
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
bonjour   1/1     1            1           6s
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
bonjour   3/3     3            3           8s
```

Both values are there. Each `upgrade` created a revision:

```bash
helm history bonjour -n essai-chart
```

```text
REVISION	UPDATED                 	STATUS    	CHART        	APP VERSION	DESCRIPTION     
1       	Thu Nov 19 19:52:13 2026	superseded	bonjour-0.1.0	1.16.0     	Install complete
2       	Thu Nov 19 19:52:15 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
3       	Thu Nov 19 19:52:17 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
4       	Thu Nov 19 19:52:17 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
5       	Thu Nov 19 19:52:19 2026	deployed  	bonjour-0.1.0	1.16.0     	Upgrade complete
```

The `APP VERSION` column shows `1.16.0`, the chart's `appVersion`, while the
image runs 1.30.5: this column copies `Chart.yaml`, it does not read the image.

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
1       	Thu Nov 19 19:52:13 2026	superseded	bonjour-0.1.0	1.16.0     	Install complete
2       	Thu Nov 19 19:52:15 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
3       	Thu Nov 19 19:52:17 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
4       	Thu Nov 19 19:52:17 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
5       	Thu Nov 19 19:52:19 2026	superseded	bonjour-0.1.0	1.16.0     	Upgrade complete
6       	Thu Nov 19 19:52:21 2026	deployed  	bonjour-0.1.0	1.16.0     	Rollback to 2   
USER-SUPPLIED VALUES:
replicaCount: 3
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
bonjour   3/3     3            3           12s
```

A revision 6 appeared (`Rollback to 2`), with the values of revision 2:
3 replicas, no more label. Finally, check that the application answers, on the
internal address of its Service (`grep -o` keeps only the page title):

```bash
IP=$(kubectl get service bonjour -n essai-chart -o jsonpath='{.spec.clusterIP}'); curl -s "http://$IP" | grep -o '<title>.*</title>'
```

```text
<title>Welcome to nginx!</title>
```

## 🧹 Clean up

Uninstall the release, delete its namespace and the trial chart:

```bash
helm uninstall bonjour -n essai-chart --wait; kubectl delete namespace essai-chart; rm -rf ~/essai-charts
```

```text
release "bonjour" uninstalled
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
move it to two replicas, then go back to its first revision.

```bash
dsoxlab run ckad-helm-install-upgrade
dsoxlab challenge ckad-helm-install-upgrade
```
