# Override the values of a Helm chart

A Helm chart is tuned through its **values**: the number of replicas, a colour,
a message. The chart holds default values, and you **override** them (you
replace them) with a file or on the command line. In this course, you compare
the values of two versions of a chart, you read the settings of a release
someone else installed, you see how `--set` guesses the type of a value, then
you upgrade while taking those settings back, in two ways.

You work with a trial release, `vitrail`, of the podinfo chart, in a scratch
namespace, `essai-values`. The challenge is about another release: you will do
it on your own, at the end.

Related page: [Helm values](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/tools/helm/helm-values/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-surcharger-les-values-d-un-chart-helm
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it, the lab installed Helm
and declared the `podinfo` repository.

The outputs shown in this course were recorded on this machine on 20 November
2026, with Kubernetes v1.37.2 and Helm 4.3.2.

## 📚 Exercise 1: what a version adds to the values

`helm show values` shows the default values of a chart, without installing
anything. Compare those of versions 6.16.0 and 6.17.0 of podinfo:

```bash
diff <(helm show values podinfo/podinfo --version 6.16.0) <(helm show values podinfo/podinfo --version 6.17.0); echo "diff : code $?"
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
diff : code 1
```

Two changes. The image tag follows the version. And 6.17.0 **adds** two
values under `spiffe`, `backendMTLS` and `backendIDs`, which did not exist in
6.16.0. Keep them in mind: exercise 7 shows that an upgrade can forget them.
A few values you are going to change:

```bash
helm show values podinfo/podinfo --version 6.17.0 | grep -n -E '^replicaCount|^ui:|^  color|^  message|^  logo'
```

```text
3:replicaCount: 1
17:ui:
18:  color: "#34577c"
19:  message: ""
20:  logo: ""
```

Values are laid out as in YAML: `color` is **under** `ui`, so you write it
`ui.color`. By default: 1 replica, a blue colour, no message.

## 📚 Exercise 2: a release installed by someone else

A colleague installs a release with their settings, passed on the command
line ("Bonjour" means "Hello"). They leave no file behind:

```bash
kubectl create namespace essai-values
helm install vitrail podinfo/podinfo --version 6.16.0 -n essai-values --set replicaCount=2 --set ui.color=#2a9d8f --set ui.message=Bonjour --wait --timeout 180s | head -5
```

```text
namespace/essai-values created
NAME: vitrail
LAST DEPLOYED: Fri Nov 20 19:12:39 2026
NAMESPACE: essai-values
STATUS: deployed
REVISION: 1
```

You take this release over. The settings are nowhere on disk, but Helm keeps
them in the cluster. `helm get values` shows the values the release received:

```bash
helm get values vitrail -n essai-values
```

```text
USER-SUPPLIED VALUES:
replicaCount: 2
ui:
  color: '#2a9d8f'
  message: Bonjour
```

`--all` adds all the chart's default values, to see everything that applies:

```bash
helm get values vitrail -n essai-values --all | grep -n -E '^replicaCount|^  color|^  message|^  logo'
```

```text
143:replicaCount: 2
181:  color: '#2a9d8f'
182:  logo: ""
183:  message: Bonjour
```

The colleague's three values replaced the defaults. `logo`, which nobody
touched, keeps its own.

## 📚 Exercise 3: read what the application answers

podinfo answers on port 9898 of its Service, with a small JSON document.
`grep` keeps the version, the colour and the message:

```bash
IP=$(kubectl get service vitrail-podinfo -n essai-values -o jsonpath='{.spec.clusterIP}'); curl -s "http://$IP:9898" | grep -E '"(version|color|message)"'
```

```text
  "version": "6.16.0",
  "color": "#2a9d8f",
  "message": "Bonjour",
```

The application does apply these values.

## 📚 Exercise 4: --set guesses the type

`--set` sets a value on the command line. `--reuse-values` keeps the values
already passed. Change the message to `1984`, without changing version:

```bash
helm upgrade vitrail podinfo/podinfo --version 6.16.0 -n essai-values --reuse-values --set ui.message=1984 --wait --timeout 180s > /dev/null; echo "upgrade : code $?"
```

```text
upgrade : code 0
```

Read the values as JSON (`-o json`), which shows the type of each value:

```bash
helm get values vitrail -n essai-values -o json; echo
```

```text
{"replicaCount":2,"ui":{"color":"#2a9d8f","message":1984}}
```

`"#2a9d8f"` is in quotes: it is text. `1984` is not: `--set` saw a number and
stored it as an **integer**. In the same way, `--set` turns `true` and `false`
into booleans, and `null` into "no value". Yet the upgrade succeeded:

```bash
helm history vitrail -n essai-values | tail -1 | cut -c1-120
kubectl get deployment vitrail-podinfo -n essai-values -o jsonpath='{.spec.template.spec.containers[0].env}'; echo
```

```text
2       	Fri Nov 20 19:12:41 2026	deployed  	podinfo-6.16.0	6.16.0     	Upgrade complete
[{"name":"PODINFO_UI_MESSAGE","value":"1984"},{"name":"PODINFO_UI_COLOR","value":"#2a9d8f"}]
```

This chart turns the value back into text when it writes the container's
environment variable. But the release kept an integer: that is not what you
meant to write, and another chart could use it as it is.

## 📚 Exercise 5: --set-string keeps a string

`--set-string` sets the value as text, whatever it holds:

```bash
helm upgrade vitrail podinfo/podinfo --version 6.16.0 -n essai-values --reuse-values --set-string ui.message=1984 --wait --timeout 180s > /dev/null; echo "upgrade : code $?"
helm get values vitrail -n essai-values -o json; echo
```

```text
upgrade : code 0
{"replicaCount":2,"ui":{"color":"#2a9d8f","message":"1984"}}
```

This time, `"1984"` is in quotes: it is a string. A values file where the value
is written in quotes (`message: "1984"`) gives the same result.

## 📚 Exercise 6: the upgrade that loses the settings, and taking them back

Move to version 6.17.0 with a new message, and nothing else:

```bash
helm upgrade vitrail podinfo/podinfo --version 6.17.0 -n essai-values --set-string ui.message=Salut --wait --timeout 180s > /dev/null; helm get values vitrail -n essai-values; kubectl get deployment vitrail-podinfo -n essai-values
```

```text
USER-SUPPLIED VALUES:
ui:
  message: Salut
NAME              READY   UP-TO-DATE   AVAILABLE   AGE
vitrail-podinfo   1/1     1            1           8s
```

The 2 replicas and the colour are gone: back to 1 replica. As soon as an
`upgrade` receives a value, Helm starts again from the chart's defaults, plus
only the values of this command. The colleague's settings are not lost,
though: each revision keeps its own.

```bash
helm history vitrail -n essai-values | cut -c1-110
```

```text
REVISION	UPDATED                 	STATUS    	CHART         	APP VERSION	DESCRIPTION     
1       	Fri Nov 20 19:12:39 2026	superseded	podinfo-6.16.0	6.16.0     	Install complete
2       	Fri Nov 20 19:12:41 2026	superseded	podinfo-6.16.0	6.16.0     	Upgrade complete
3       	Fri Nov 20 19:12:44 2026	superseded	podinfo-6.16.0	6.16.0     	Upgrade complete
4       	Fri Nov 20 19:12:45 2026	deployed  	podinfo-6.17.0	6.17.0     	Upgrade complete
```

Revision 3 is the last one that carried the full settings. Save its values in
a file (`-o yaml` gives a reusable values file):

```bash
helm get values vitrail -n essai-values --revision 3 -o yaml > ~/reprise.yaml; cat ~/reprise.yaml
```

```text
replicaCount: 2
ui:
  color: '#2a9d8f'
  message: "1984"
```

Pass this file back with `-f`, then the new message ("Salut" means "Hi"):

```bash
helm upgrade vitrail podinfo/podinfo --version 6.17.0 -n essai-values -f ~/reprise.yaml --set-string ui.message=Salut --wait --timeout 180s > /dev/null; helm get values vitrail -n essai-values; kubectl get deployment vitrail-podinfo -n essai-values
```

```text
USER-SUPPLIED VALUES:
replicaCount: 2
ui:
  color: '#2a9d8f'
  message: Salut
NAME              READY   UP-TO-DATE   AVAILABLE   AGE
vitrail-podinfo   2/2     2            2           11s
```

The file gives back the 2 replicas and the colour. `--set-string`, read after
the file, wins for the message: `Salut` replaces `1984`. When a value is given
twice, the last one wins. And since Helm started again from the 6.17.0
defaults, the two values added by this version are there:

```bash
helm get values vitrail -n essai-values --all | grep -n -E 'backend(MTLS|IDs)'
```

```text
171:  backendIDs: []
172:  backendMTLS: false
```

## 📚 Exercise 7: --reuse-values or --reset-then-reuse-values

Why not simply upgrade with `--reuse-values`? Go back to revision 3, in
6.16.0, and check that the two 6.17.0 values are not there (`grep -c` counts
the lines found):

```bash
helm rollback vitrail 3 -n essai-values --wait --timeout 180s; helm get values vitrail -n essai-values --all | grep -c -E 'backend(MTLS|IDs)'
```

```text
Rollback was a success! Happy Helming!
0
```

Upgrade to 6.17.0 with `--reuse-values`:

```bash
helm upgrade vitrail podinfo/podinfo --version 6.17.0 -n essai-values --reuse-values --set ui.message=Reprise --wait --timeout 180s > /dev/null; helm history vitrail -n essai-values | tail -1 | cut -c1-110; helm get values vitrail -n essai-values --all | grep -n -E 'backend(MTLS|IDs)'; echo "grep : code $?"
```

```text
7       	Fri Nov 20 19:12:53 2026	deployed  	podinfo-6.17.0	6.17.0     	Upgrade complete
grep : code 1
```

The release runs 6.17.0, but `grep` finds nothing (code 1): the two values
added by 6.17.0 are missing. `--reuse-values` takes back **all** the values of
the previous revision, the old version's defaults included, and ignores
those of the new version. Here, the chart copes. Another chart, whose
template reads a new value, may fail or produce a wrong manifest.

`--reset-then-reuse-values` sorts this out: it starts again from the new
version's defaults, then puts back only the values the release had received.
Go back to revision 3 and start again with this option:

```bash
helm rollback vitrail 3 -n essai-values --wait --timeout 180s > /dev/null; helm upgrade vitrail podinfo/podinfo --version 6.17.0 -n essai-values --reset-then-reuse-values --set ui.message=Reprise --wait --timeout 180s > /dev/null; helm history vitrail -n essai-values | tail -1 | cut -c1-110; helm get values vitrail -n essai-values
```

```text
9       	Fri Nov 20 19:13:18 2026	deployed  	podinfo-6.17.0	6.17.0     	Upgrade complete
USER-SUPPLIED VALUES:
replicaCount: 2
ui:
  color: '#2a9d8f'
  message: Reprise
```

The settings are taken back, and so are the new 6.17.0 values:

```bash
helm get values vitrail -n essai-values --all | grep -n -E 'backend(MTLS|IDs)'
```

```text
171:  backendIDs: []
172:  backendMTLS: false
```

The application runs 6.17.0 with all its settings (the `sleep` gives the old
Pods time to stop):

```bash
sleep 10; IP=$(kubectl get service vitrail-podinfo -n essai-values -o jsonpath='{.spec.clusterIP}'); curl -s "http://$IP:9898" | grep -E '"(version|color|message)"'
```

```text
  "version": "6.17.0",
  "color": "#2a9d8f",
  "message": "Reprise",
```

## 🧹 Clean up

Uninstall the release, delete its namespace and the saved values file:

```bash
helm uninstall vitrail -n essai-values --wait; kubectl delete namespace essai-values; rm -f ~/reprise.yaml
```

```text
release "vitrail" uninstalled
namespace "essai-values" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-surcharger-les-values-d-un-chart-helm
dsoxlab check k8s-surcharger-les-values-d-un-chart-helm
```

```text
╭─ Result: k8s-surcharger-les-values-d-un-chart-helm ─╮
│  0 / 100 pts                                        │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests                    │
╰─────────────────────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: another release, tuned by someone else.
Upgrade it and change its message, without losing its settings or falling into
the type trap.

```bash
dsoxlab run k8s-surcharger-les-values-d-un-chart-helm
dsoxlab challenge k8s-surcharger-les-values-d-un-chart-helm
```
