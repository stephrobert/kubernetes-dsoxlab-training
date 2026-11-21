# Make an application 12-factor compliant on Kubernetes

The lesson takes an application over factor by factor: configuration,
attached resource, state, clean shutdown and administration task. This course
pushes each of these gestures to where it breaks: a missing configuration, a
misaddressed cache that the application's probe does not see, unusual key
names, a `preStop` too long for the shutdown delay, and a Job that cannot be
fixed in place.

You work in a scratch namespace, `essai-douze`, with an application `vitrine`
("showcase", podinfo) and a Redis cache `cache`. The challenge is about
another application: you will do it on your own, at the end.

Related page: [Make an application 12-factor compliant on Kubernetes](https://www.stephane-robert.info/en/docs/conteneurs/cloud-native/application-12-factor-kubernetes/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-rendre-une-application-conforme-12-facteurs
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2 and podinfo 6.17.0.

First create the scratch namespace and a Redis cache, exposed by a Service:

```bash
kubectl create namespace essai-douze
kubectl create deployment cache --image=redis:7.4.11-alpine@sha256:858f009f9709ce576febc734aa78b8f6d624b82571f9ddb6bda4377c833b3499 -n essai-douze; kubectl expose deployment cache --port=6379 -n essai-douze; kubectl rollout status deployment/cache -n essai-douze --timeout=120s
```

```text
namespace/essai-douze created
deployment.apps/cache created
service/cache exposed
Waiting for deployment "cache" rollout to finish: 0 of 1 updated replicas are available...
deployment "cache" successfully rolled out
```

## 📚 Exercise 1: a configuration that does not exist yet

Deploy `vitrine`. Its configuration comes from a ConfigMap, `vitrine-config`,
through `envFrom`. That ConfigMap does not exist yet:

```bash
mkdir -p ~/essai-douze && cat > ~/essai-douze/vitrine.yaml <<YAML
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vitrine
  namespace: essai-douze
spec:
  replicas: 1
  selector:
    matchLabels: {app: vitrine}
  template:
    metadata:
      labels: {app: vitrine}
    spec:
      containers:
        - name: vitrine
          image: ghcr.io/stefanprodan/podinfo:6.17.0@sha256:fa2f27c1a8561097e5144bfc0853eba6054d743b68b03de4cad4675616ddefb0
          envFrom:
            - configMapRef:
                name: vitrine-config
YAML
kubectl apply -f ~/essai-douze/vitrine.yaml
```

```text
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vitrine
  namespace: essai-douze
spec:
  replicas: 1
  selector:
    matchLabels: {app: vitrine}
  template:
    metadata:
      labels: {app: vitrine}
    spec:
      containers:
        - name: vitrine
          image: ghcr.io/stefanprodan/podinfo:6.17.0@sha256:fa2f27c1a8561097e5144bfc0853eba6054d743b68b03de4cad4675616ddefb0
          envFrom:
            - configMapRef:
                name: vitrine-config
YAML
kubectl apply -f ~/essai-douze/vitrine.yaml
deployment.apps/vitrine created
```

The Deployment is accepted. Look at the Pod after a few seconds:

```bash
sleep 15; kubectl get pods -n essai-douze -l app=vitrine
```

```text
NAME                       READY   STATUS                       RESTARTS   AGE
vitrine-7bb897cb9d-7r788   0/1     CreateContainerConfigError   0          15s
```

`CreateContainerConfigError`: the kubelet cannot build the container's
environment. The event says why:

```bash
kubectl get events -n essai-douze --field-selector reason=Failed -o custom-columns=MESSAGE:.message | tail -2
```

```text
MESSAGE
Error: configmap "vitrine-config" not found
```

Create the ConfigMap ("bonjour" means "hello"). The Pod starts on its own,
without being recreated:

```bash
kubectl create configmap vitrine-config -n essai-douze --from-literal=PODINFO_UI_MESSAGE=bonjour --from-literal=PODINFO_CACHE_SERVER=tcp://cache:6379; kubectl rollout status deployment/vitrine -n essai-douze --timeout=120s; kubectl get pods -n essai-douze -l app=vitrine
```

```text
configmap/vitrine-config created
Waiting for deployment "vitrine" rollout to finish: 0 of 1 updated replicas are available...
deployment "vitrine" successfully rolled out
NAME                       READY   STATUS    RESTARTS   AGE
vitrine-7bb897cb9d-7r788   1/1     Running   0          24s
```

The Pod keeps its name: the kubelet tried again and found the ConfigMap.
Expose the application for what follows:

```bash
kubectl expose deployment vitrine --name=vitrine-svc --port=80 --target-port=9898 -n essai-douze
```

```text
service/vitrine-svc exposed
```

## 📚 Exercise 2: `optional`, and what it hides

A reference with `optional: true` lets the container start even if the
ConfigMap is missing. Delete the ConfigMap, then make the reference optional:

```bash
kubectl delete configmap vitrine-config -n essai-douze; kubectl patch deployment vitrine -n essai-douze --type json -p '[{"op":"add","path":"/spec/template/spec/containers/0/envFrom/0/configMapRef/optional","value":true}]'; kubectl rollout status deployment/vitrine -n essai-douze --timeout=120s
```

```text
configmap "vitrine-config" deleted from essai-douze namespace
deployment.apps/vitrine patched
Waiting for deployment "vitrine" rollout to finish: 0 out of 1 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
deployment "vitrine" successfully rolled out
```

The application runs. But it runs with no configuration at all:

```bash
kubectl exec deploy/vitrine -n essai-douze -- env | grep '^PODINFO_' ; echo "grep : code $?"
```

```text
grep : code 1
```

No `PODINFO_` variable. Nothing reports the absence: the Pod is `Running`
and the failure will show later, in the behaviour of the application.
`optional` suits a truly optional setting, never the configuration the
application needs.

## 📚 Exercise 3: a misaddressed cache

Recreate the ConfigMap with a mistake: port 6380 instead of 6379. Restart the
Deployment so that the new Pod reads it:

```bash
kubectl create configmap vitrine-config -n essai-douze --from-literal=PODINFO_UI_MESSAGE=bonjour --from-literal=PODINFO_CACHE_SERVER=tcp://cache:6380; kubectl rollout restart deployment/vitrine -n essai-douze; kubectl rollout status deployment/vitrine -n essai-douze --timeout=120s
```

```text
configmap/vitrine-config created
deployment.apps/vitrine restarted
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
deployment "vitrine" successfully rolled out
```

Write a value into podinfo's cache, then read it back, from the node, on the
address of the Service ("écriture" means write, "lecture" read):

```bash
IP=$(kubectl get service vitrine-svc -n essai-douze -o jsonpath='{.spec.clusterIP}'); curl -s -m 5 -o /dev/null -w 'écriture : %{http_code}\n' -X POST -d essai "http://$IP/cache/cle"; curl -s -m 5 -w ' lecture : %{http_code}\n' "http://$IP/cache/cle"
```

```text
écriture : 200
{
  "code": 400,
  "message": "cache server is offline"
} lecture : 200
```

Both requests return 200, but the read says `cache server is offline`. Is the
application declared ready?

```bash
IP=$(kubectl get service vitrine-svc -n essai-douze -o jsonpath='{.spec.clusterIP}'); curl -s -m 5 "http://$IP/readyz"; echo; kubectl get pods -n essai-douze -l app=vitrine
```

```text
{
  "status": "OK"
}
NAME                       READY   STATUS        RESTARTS   AGE
vitrine-6bdfc6b45-68drb    1/1     Terminating   0          2s
vitrine-7bb897cb9d-7r788   1/1     Terminating   0          26s
vitrine-9d46bbc58-m4lkn    1/1     Running       0          1s
```

Yes: `/readyz` answers `OK`, and the new Pod is `1/1`. podinfo's probe does
not check its cache. An unreachable attached resource therefore shows neither
in the state of the Pod nor in its conditions: you have to query the
application itself. Fix the port:

```bash
kubectl patch configmap vitrine-config -n essai-douze --type merge -p '{"data":{"PODINFO_CACHE_SERVER":"tcp://cache:6379"}}'; kubectl rollout restart deployment/vitrine -n essai-douze; kubectl rollout status deployment/vitrine -n essai-douze --timeout=120s
```

```text
configmap/vitrine-config patched
deployment.apps/vitrine restarted
Waiting for deployment "vitrine" rollout to finish: 0 out of 1 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
deployment "vitrine" successfully rolled out
```

Write again. Give the new Pod ten seconds: on this machine, a write sent right
after the restart timed out, and the same write, ten seconds later, succeeded.

```bash
sleep 10; IP=$(kubectl get service vitrine-svc -n essai-douze -o jsonpath='{.spec.clusterIP}'); curl -s -m 5 -o /dev/null -w 'écriture : %{http_code}\n' -X POST -d essai "http://$IP/cache/cle"; curl -s -m 5 -w ' lecture : %{http_code}\n' "http://$IP/cache/cle"
```

```text
écriture : 202
essai lecture : 200
```

`202` on the write, and the read returns the value `essai`.

## 📚 Exercise 4: keys that do not look like variables

Add two keys with unusual names to the ConfigMap: one holds a dot, the other
starts with a digit ("couleur" means "colour").

```bash
kubectl patch configmap vitrine-config -n essai-douze --type merge -p '{"data":{"ui.couleur":"#ff6b00","1PODINFO_X":"oui"}}'; kubectl rollout restart deployment/vitrine -n essai-douze; kubectl rollout status deployment/vitrine -n essai-douze --timeout=120s
```

```text
configmap/vitrine-config patched
deployment.apps/vitrine restarted
Waiting for deployment spec update to be observed...
Waiting for deployment "vitrine" rollout to finish: 0 out of 1 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
deployment "vitrine" successfully rolled out
```

```bash
kubectl exec deploy/vitrine -n essai-douze -- env | grep -E 'couleur|PODINFO_X'; echo "grep : code $?"
```

```text
ui.couleur=#ff6b00
1PODINFO_X=oui
grep : code 0
```

Kubernetes 1.37 passes both to the container. But a shell cannot read them:

```bash
kubectl exec deploy/vitrine -n essai-douze -- sh -c 'echo "PODINFO_UI_MESSAGE=[$PODINFO_UI_MESSAGE]"; echo "ui.couleur=[$ui.couleur]"'
```

```text
PODINFO_UI_MESSAGE=[bonjour]
ui.couleur=[.couleur]
```

`$ui.couleur` reads as `$ui` (empty) followed by the text `.couleur`. The
variable exists, but a shell script cannot reach it. For a configuration that
any program can read, keep names made of capitals, digits and underscores,
that do not start with a digit.

## 📚 Exercise 5: a `preStop` longer than the shutdown delay

The `preStop` hook delays the stop of the container, to finish the requests
in progress. Ask for a 20-second pause with a shutdown delay
(`terminationGracePeriodSeconds`) of 5 seconds:

```bash
kubectl patch deployment vitrine -n essai-douze --type strategic -p '{"spec":{"template":{"spec":{"terminationGracePeriodSeconds":5,"containers":[{"name":"vitrine","lifecycle":{"preStop":{"sleep":{"seconds":20}}}}]}}}}'
```

```text
The Deployment "vitrine" is invalid: spec.template.spec.containers[0].lifecycle.preStop.sleep: Invalid value: 20: must be non-negative and less than terminationGracePeriodSeconds (5)
```

The API refuses: the pause must be shorter than the shutdown delay, otherwise
the container would be killed in the middle of its pause. Give 8 seconds of
pause for a 10-second delay:

```bash
kubectl patch deployment vitrine -n essai-douze --type strategic -p '{"spec":{"template":{"spec":{"terminationGracePeriodSeconds":10,"containers":[{"name":"vitrine","lifecycle":{"preStop":{"sleep":{"seconds":8}}}}]}}}}'; kubectl rollout status deployment/vitrine -n essai-douze --timeout=120s
```

```text
deployment.apps/vitrine patched
Waiting for deployment spec update to be observed...
Waiting for deployment "vitrine" rollout to finish: 0 out of 1 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
deployment "vitrine" successfully rolled out
```

Wait until the old Pod is gone, then time the deletion of the new one
("suppression" means deletion):

```bash
sleep 12; kubectl get pods -n essai-douze -l app=vitrine; P=$(kubectl get pod -n essai-douze -l app=vitrine -o name | head -1); debut=$(date +%s); kubectl delete $P -n essai-douze; echo "suppression : $(( $(date +%s) - debut )) s"
```

```text
NAME                       READY   STATUS    RESTARTS   AGE
vitrine-5fd85ff7c9-phh4d   1/1     Running   0          13s
pod "vitrine-5fd85ff7c9-phh4d" deleted from essai-douze namespace
suppression : 11 s
```

The deletion took the time of the pause, plus the stop of the application.
That delay lets the Service remove the Pod from its addresses before the
container stops.

## 📚 Exercise 6: an administration Job that fails, then is changed

Write a Job that reads the version of the application. It targets port 9898,
the container's port, while the Service listens on port 80:

```bash
cat > ~/essai-douze/version.yaml <<YAML
apiVersion: batch/v1
kind: Job
metadata:
  name: version-lue
  namespace: essai-douze
spec:
  backoffLimit: 1
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: lire
          image: ghcr.io/stefanprodan/podinfo:6.17.0@sha256:fa2f27c1a8561097e5144bfc0853eba6054d743b68b03de4cad4675616ddefb0
          command: ["sh", "-c", "wget -qO- -T 3 http://vitrine-svc:9898/version"]
YAML
kubectl apply -f ~/essai-douze/version.yaml; kubectl wait --for=condition=Failed job/version-lue -n essai-douze --timeout=120s
```

```text
apiVersion: batch/v1
kind: Job
metadata:
  name: version-lue
  namespace: essai-douze
spec:
  backoffLimit: 1
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: lire
          image: ghcr.io/stefanprodan/podinfo:6.17.0@sha256:fa2f27c1a8561097e5144bfc0853eba6054d743b68b03de4cad4675616ddefb0
          command: ["sh", "-c", "wget -qO- -T 3 http://vitrine-svc:9898/version"]
YAML
kubectl apply -f ~/essai-douze/version.yaml; kubectl wait --for=condition=Failed job/version-lue -n essai-douze --timeout=120s
job.batch/version-lue created
job.batch/version-lue condition met
```

```bash
kubectl get pods -n essai-douze -l job-name=version-lue; kubectl logs -n essai-douze -l job-name=version-lue --tail=1
```

```text
NAME                READY   STATUS   RESTARTS   AGE
version-lue-58vxn   0/1     Error    0          6s
version-lue-s6c97   0/1     Error    0          20s
wget: download timed out
wget: download timed out
```

Two Pods in `Error`: the first attempt, plus the retry that `backoffLimit: 1`
allows. Fix the port in the file, then apply again:

```bash
sed -i 's|vitrine-svc:9898|vitrine-svc|' ~/essai-douze/version.yaml; kubectl apply -f ~/essai-douze/version.yaml 2>&1 | tail -2 | cut -c1-120
```

```text
The Job "version-lue" is invalid: spec.template: Invalid value: {"labels":{"batch.kubernetes.io/controller-uid":"dba3def
```

The API refuses: the template of a Job (`spec.template`) cannot be changed
(`field is immutable`). A Job is deleted, then recreated:

```bash
kubectl delete job version-lue -n essai-douze; kubectl apply -f ~/essai-douze/version.yaml; kubectl wait --for=condition=Complete job/version-lue -n essai-douze --timeout=120s; kubectl logs job/version-lue -n essai-douze; echo
```

```text
job.batch "version-lue" deleted from essai-douze namespace
job.batch/version-lue created
job.batch/version-lue condition met
{
  "commit": "fd3a834ed8d14b80ea334cf8a2fddd4597924da6",
  "version": "6.17.0"
}
```

## 🧹 Clean up

Delete the scratch namespace and the working directory:

```bash
kubectl delete namespace essai-douze; rm -rf ~/essai-douze
```

```text
namespace "essai-douze" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-rendre-une-application-conforme-12-facteurs
dsoxlab check k8s-rendre-une-application-conforme-12-facteurs
```

```text
╭─ Result: k8s-rendre-une-application-conforme-12-facteurs ─╮
│  0 / 100 pts                                              │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests                          │
╰───────────────────────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a faulty application to make compliant,
factor by factor, from its configuration to its administration task.

```bash
dsoxlab run k8s-rendre-une-application-conforme-12-facteurs
dsoxlab challenge k8s-rendre-une-application-conforme-12-facteurs
```
