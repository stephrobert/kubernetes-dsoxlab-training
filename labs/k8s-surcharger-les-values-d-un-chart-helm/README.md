# Override the values of a Helm chart

A Helm chart is tuned through its **values**: the number of replicas, a colour,
a message. The chart holds default values, and you **override** them (you
replace them) with a file or on the command line. In this course, you read the
default values of a chart, you install with a values file, you read what the
application answers, you see how `--set` guesses the type of a value, and you
upgrade without losing your settings.

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

The outputs shown in this course were recorded on this machine on 19 November
2026, with Kubernetes v1.37.2 and Helm 4.3.2.

## 📚 Exercise 1: the default values of a chart

`helm show values` shows the default values of a chart, without installing
anything. `grep` keeps a few of them:

```bash
helm show values podinfo/podinfo --version 6.16.0 | grep -n -E '^replicaCount|^ui:|^  color|^  message|^  logo'
```

```text
3:replicaCount: 1
17:ui:
18:  color: "#34577c"
19:  message: ""
20:  logo: ""
```

Values are organised as in YAML: `color` is **under** `ui`, so you write it
`ui.color`. By default: 1 replica, a blue colour, no message. The chart offers
many more:

```bash
helm show values podinfo/podinfo --version 6.16.0 | wc -l
```

```text
322
```

322 lines. You change only a few of them, the rest keeps its default value.

## 📚 Exercise 2: install with a values file

Write your settings in a file: 2 replicas, a green colour and a message
("Bonjour" means "Hello"). The quotes around the colour are needed: in YAML, an
unprotected `#` starts a comment.

```bash
mkdir -p ~/essai-values && cat > ~/essai-values/reglages.yaml <<'YAML'
replicaCount: 2
ui:
  color: "#2a9d8f"
  message: Bonjour
YAML
cat ~/essai-values/reglages.yaml
```

```text
replicaCount: 2
ui:
  color: "#2a9d8f"
  message: Bonjour
```

Create the scratch namespace, then install the chart with this file (`-f`):

```bash
kubectl create namespace essai-values
helm install vitrail podinfo/podinfo --version 6.16.0 -n essai-values -f ~/essai-values/reglages.yaml --wait --timeout 180s | head -5
```

```text
namespace/essai-values created
NAME: vitrail
LAST DEPLOYED: Thu Nov 19 19:57:07 2026
NAMESPACE: essai-values
STATUS: deployed
REVISION: 1
```

`helm get values` shows the values the release received from you:

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

Your three values replaced the defaults. `logo`, which you did not touch, keeps
its own.

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

The application does apply your values.

## 📚 Exercise 4: --set guesses the type

`--set` sets a value on the command line. `--reuse-values` keeps the values
already passed. Change the message to `1984`:

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
2       	Thu Nov 19 19:57:16 2026	deployed  	podinfo-6.16.0	6.16.0     	Upgrade complete
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
is written in quotes (`message: "1984"`) gives the same result. The
application shows the message:

```bash
IP=$(kubectl get service vitrail-podinfo -n essai-values -o jsonpath='{.spec.clusterIP}'); curl -s "http://$IP:9898" | grep -E '"(version|color|message)"'
```

```text
  "version": "6.16.0",
  "color": "#2a9d8f",
  "message": "1984",
```

## 📚 Exercise 6: upgrade without losing your settings

Move to version 6.17.0 of the chart with a new message ("Salut" means "Hi"),
**without** `--reuse-values`:

```bash
helm upgrade vitrail podinfo/podinfo --version 6.17.0 -n essai-values --set-string ui.message=Salut --wait --timeout 180s > /dev/null; helm get values vitrail -n essai-values; kubectl get deployment vitrail-podinfo -n essai-values
```

```text
USER-SUPPLIED VALUES:
ui:
  message: Salut
NAME              READY   UP-TO-DATE   AVAILABLE   AGE
vitrail-podinfo   1/1     1            1           29s
```

The 2 replicas and the colour are gone: back to 1 replica. As soon as an
`upgrade` receives a value, Helm starts again from the chart's defaults, plus
only the values of this command. To keep your settings, pass the values file
again on top of the new message:

```bash
helm upgrade vitrail podinfo/podinfo --version 6.17.0 -n essai-values -f ~/essai-values/reglages.yaml --set-string ui.message=Salut --wait --timeout 180s > /dev/null; helm get values vitrail -n essai-values; kubectl get deployment vitrail-podinfo -n essai-values
```

```text
USER-SUPPLIED VALUES:
replicaCount: 2
ui:
  color: '#2a9d8f'
  message: Salut
NAME              READY   UP-TO-DATE   AVAILABLE   AGE
vitrail-podinfo   2/2     2            2           41s
```

The file brings back the 2 replicas and the colour. `--set-string`, read after
the file, wins for the message: `Salut` replaces `Bonjour`. When a value is
given twice, the last one wins. The application runs 6.17.0 with all your
settings:

```bash
IP=$(kubectl get service vitrail-podinfo -n essai-values -o jsonpath='{.spec.clusterIP}'); curl -s "http://$IP:9898" | grep -E '"(version|color|message)"'
```

```text
  "version": "6.17.0",
  "color": "#2a9d8f",
  "message": "Salut",
```

## 🧹 Clean up

Uninstall the release, delete its namespace and the values file:

```bash
helm uninstall vitrail -n essai-values --wait; kubectl delete namespace essai-values; rm -rf ~/essai-values
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
