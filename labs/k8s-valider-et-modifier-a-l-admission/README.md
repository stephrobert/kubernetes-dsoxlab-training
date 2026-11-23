# Validate and modify at admission

The lesson shows where admission controllers sit, which controllers are
active by default, how a MutatingAdmissionPolicy and a
ValidatingAdmissionPolicy act without a webhook, and how to diagnose a webhook
that does not answer. This course has you perform each of these steps on the
cluster, with other rules than the challenge's: a `cours` label, a ban on
`hostPID` and a webhook on ConfigMaps.

You work in the `essai-admission` and `essai-temoin` namespaces. The
challenge uses other namespaces and other rules: you will do it on your own,
at the end.

Related page: [Kubernetes Admission Controllers](https://www.stephane-robert.info/en/docs/devsecops/runtime/admission-controllers/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-valider-et-modifier-a-l-admission
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm
cluster (the control plane). Your kubectl already targets it.

The outputs shown in this course were captured on this machine on
23 November 2026, with Kubernetes v1.37.2.

## 📋 Exercise 1: rebuild the list of active controllers

The API server manifest gives only part of the list. Read it, then extract
from the binary's help the list of controllers enabled by default, and store
it in a file:

```bash
sudo grep admission-plugins /etc/kubernetes/manifests/kube-apiserver.yaml
kubectl -n kube-system exec kube-apiserver-k8s-cp.lab -- kube-apiserver --help 2>/dev/null \
  | grep -o 'default enabled ones ([^)]*)' | cut -d'(' -f2 | tr -d ') ' | tr ',' '\n' > defaut.txt
wc -l < defaut.txt
grep -c -x NodeRestriction defaut.txt
grep -x -e PodSecurity -e MutatingAdmissionPolicy -e ValidatingAdmissionPolicy defaut.txt
```

```text
    - --enable-admission-plugins=NodeRestriction
25
0
PodSecurity
MutatingAdmissionPolicy
ValidatingAdmissionPolicy
```

The manifest only enables `NodeRestriction`, but this flag **adds** to the
default list, it does not replace it. The default list holds 25 controllers,
and `NodeRestriction` is not one of them: that is why kubeadm adds it. The
three controllers of the last command are active without installing
anything. They are the ones used in the rest of this course.

## 🔀 Exercise 2: mutation runs before validation

Create the scratch namespace and a ValidatingAdmissionPolicy that requires
the `cours` label on every Pod created in `essai-admission`. Test it with
`--dry-run=server`: the request goes through the whole admission chain, but
nothing is stored.

```bash
kubectl create namespace essai-admission; cat <<'YAML' | kubectl apply -f -
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: essai-exige-cours
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: [v1]
        operations: [CREATE]
        resources: [pods]
  validations:
    - expression: 'has(object.metadata.labels) && "cours" in object.metadata.labels'
      message: "un Pod de essai-admission porte le label cours"
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: essai-exige-cours
spec:
  policyName: essai-exige-cours
  validationActions: [Deny]
  matchResources:
    namespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: essai-admission
YAML
sleep 5; kubectl -n essai-admission run essai-a --image=busybox:1.37 --restart=Never --dry-run=server -- sleep 60
```

```text
namespace/essai-admission created
validatingadmissionpolicy.admissionregistration.k8s.io/essai-exige-cours created
validatingadmissionpolicybinding.admissionregistration.k8s.io/essai-exige-cours created
The pods "essai-a" is invalid: : ValidatingAdmissionPolicy 'essai-exige-cours' with binding 'essai-exige-cours' denied request: un Pod de essai-admission porte le label cours
```

The Pod is refused: `kubectl run` only sets the `run` label. Now add a
MutatingAdmissionPolicy that sets `cours: admission` on the Pods of the same
namespace, then submit the same Pod:

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingAdmissionPolicy
metadata:
  name: essai-pose-cours
spec:
  failurePolicy: Fail
  reinvocationPolicy: Never
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: [v1]
        operations: [CREATE]
        resources: [pods]
  mutations:
    - patchType: ApplyConfiguration
      applyConfiguration:
        expression: |
          Object{
            metadata: Object.metadata{
              labels: {"cours": "admission"}
            }
          }
---
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingAdmissionPolicyBinding
metadata:
  name: essai-pose-cours
spec:
  policyName: essai-pose-cours
  matchResources:
    namespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: essai-admission
YAML
sleep 5; kubectl -n essai-admission run essai-a --image=busybox:1.37 --restart=Never --dry-run=server -o jsonpath='{.metadata.labels}{"\n"}' -- sleep 60
```

```text
mutatingadmissionpolicy.admissionregistration.k8s.io/essai-pose-cours created
mutatingadmissionpolicybinding.admissionregistration.k8s.io/essai-pose-cours created
{"cours":"admission","run":"essai-a"}
```

The same Pod goes through, and it carries the `cours` label. Mutation runs
before validation: when the VAP looks at the Pod, the label is already there.

## 🧩 Exercise 3: what the merge keeps and what it overwrites

The MAP describes a partial object that the API server merges into the Pod.
Submit a Pod that already declares two labels, including `cours` with another
value:

```bash
kubectl -n essai-admission run essai-b --image=busybox:1.37 --restart=Never --labels=cours=autre,app=demo --dry-run=server -o jsonpath='{.metadata.labels}{"\n"}' -- sleep 60
```

```text
{"app":"demo","cours":"admission"}
```

The `app` label is kept: the MAP does not mention it. The `cours` label is
**overwritten** by the MAP's value. A MAP written this way enforces a value;
it does not only fill it in when it is missing.

## 🚫 Exercise 4: a rule that only applies to labelled namespaces

Create a control namespace, then a VAP that refuses Pods in `hostPID` mode
(they see the node's processes). Its binding picks namespaces by the label
`environment=essai`, which nobody has set yet. Prepare a `hostPID` Pod and
submit it:

```bash
kubectl create namespace essai-temoin; cat <<'YAML' | kubectl apply -f -
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: essai-sans-hostpid
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: [v1]
        operations: [CREATE, UPDATE]
        resources: [pods]
  validations:
    - expression: '!(has(object.spec.hostPID) && object.spec.hostPID)'
      message: "hostPID est interdit ici"
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: essai-sans-hostpid
spec:
  policyName: essai-sans-hostpid
  validationActions: [Deny]
  matchResources:
    namespaceSelector:
      matchLabels:
        environment: essai
YAML
cat > hostpid.yaml <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: essai-hostpid
  labels:
    cours: admission
spec:
  hostPID: true
  containers:
    - name: c
      image: busybox:1.37
      command: ["sleep", "60"]
YAML
sleep 5; kubectl -n essai-admission apply -f hostpid.yaml --dry-run=server
```

```text
namespace/essai-temoin created
validatingadmissionpolicy.admissionregistration.k8s.io/essai-sans-hostpid created
validatingadmissionpolicybinding.admissionregistration.k8s.io/essai-sans-hostpid created
pod/essai-hostpid created (server dry run)
```

The policy and its binding exist, and the Pod still goes through: no
namespace carries the label `environment=essai`. Set it on
`essai-admission`, then submit the Pod in both namespaces:

```bash
kubectl label namespace essai-admission environment=essai
sleep 5; kubectl -n essai-admission apply -f hostpid.yaml --dry-run=server
kubectl -n essai-temoin apply -f hostpid.yaml --dry-run=server
```

```text
namespace/essai-admission labeled
The pods "essai-hostpid" is invalid: : ValidatingAdmissionPolicy 'essai-sans-hostpid' with binding 'essai-sans-hostpid' denied request: hostPID est interdit ici
pod/essai-hostpid created (server dry run)
```

Refused in `essai-admission`, accepted in `essai-temoin`. The message names
the policy and the binding: they lead you back to the rule.

## 🩺 Exercise 5: diagnose a webhook that does not answer

Create a Service `essai-controleur` with no Pod behind it, then a validating
webhook that calls it for every ConfigMap created in `essai-admission`, with
`failurePolicy: Fail`. Try to create a ConfigMap:

```bash
kubectl -n essai-admission create service clusterip essai-controleur --tcp=443:8443
cat <<'YAML' | kubectl apply -f -
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: essai-controle-configmaps
webhooks:
  - name: controle.essai-admission.svc
    clientConfig:
      service:
        name: essai-controleur
        namespace: essai-admission
        path: /valider
    rules:
      - apiGroups: [""]
        apiVersions: [v1]
        operations: [CREATE]
        resources: [configmaps]
    namespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: essai-admission
    admissionReviewVersions: [v1]
    sideEffects: None
    failurePolicy: Fail
YAML
sleep 3; kubectl -n essai-admission create configmap essai-cm --from-literal=a=1
```

```text
service/essai-controleur created
validatingwebhookconfiguration.admissionregistration.k8s.io/essai-controle-configmaps created
error: failed to create configmap: Internal error occurred: failed calling webhook "controle.essai-admission.svc": failed to call webhook: Post "https://essai-controleur.essai-admission.svc:443/valider?timeout=10s": dial tcp 10.97.18.97:443: connect: connection refused
```

The message gives the **webhook** name, `controle.essai-admission.svc`, and
the address of the Service it calls, `essai-controleur.essai-admission.svc`.
It does not give the name of the **configuration** that holds it, and that is
the object you will have to change. Go back from the message to the cause:
find which configuration contains this webhook, read its `failurePolicy` and
its Service, then look at the endpoints of that Service.

```bash
kubectl get validatingwebhookconfigurations -o custom-columns='CONFIGURATION:.metadata.name,WEBHOOKS:.webhooks[*].name,ECHEC:.webhooks[*].failurePolicy,SERVICE:.webhooks[*].clientConfig.service.name' | grep -e CONFIGURATION -e controle.essai-admission.svc
kubectl -n essai-admission get endpointslice -l kubernetes.io/service-name=essai-controleur
```

```text
CONFIGURATION                  WEBHOOKS                       ECHEC   SERVICE
essai-controle-configmaps      controle.essai-admission.svc   Fail    essai-controleur
NAME                     ADDRESSTYPE   PORTS     ENDPOINTS   AGE
essai-controleur-9hzdv   IPv4          <unset>   <unset>     3s
```

The configuration is called `essai-controle-configmaps`. Its webhook is in
`Fail` mode (the `ECHEC` column) and its Service has no endpoint (`<unset>`):
no Pod can answer, so every ConfigMap of this namespace is refused. Switch the
webhook to `Ignore` and try again:

```bash
kubectl patch validatingwebhookconfiguration essai-controle-configmaps --type=json -p '[{"op":"replace","path":"/webhooks/0/failurePolicy","value":"Ignore"}]'
sleep 3; kubectl -n essai-admission create configmap essai-cm --from-literal=a=1
kubectl -n kube-system logs kube-apiserver-k8s-cp.lab --since=60s | grep -o 'Failed calling webhook, failing open [^:]*' | tail -1
```

```text
validatingwebhookconfiguration.admissionregistration.k8s.io/essai-controle-configmaps patched
configmap/essai-cm created
Failed calling webhook, failing open controle.essai-admission.svc
```

The ConfigMap is created without a word on the client side. Yet the webhook
checked nothing: only the API server log says so (`failing open`). That is
the trap of `Ignore`.

## 🧹 Clean-up

Webhooks, policies and their bindings belong to the cluster, not to a
namespace: delete them one by one, then the two scratch namespaces and the
file prepared in exercise 4. The last command counts the `essai` objects
left:

```bash
kubectl delete validatingwebhookconfiguration essai-controle-configmaps
kubectl delete validatingadmissionpolicybinding essai-exige-cours essai-sans-hostpid
kubectl delete validatingadmissionpolicy essai-exige-cours essai-sans-hostpid
kubectl delete mutatingadmissionpolicybinding essai-pose-cours
kubectl delete mutatingadmissionpolicy essai-pose-cours
kubectl delete namespace essai-admission essai-temoin --wait=true --timeout=120s
rm -f defaut.txt hostpid.yaml
kubectl get validatingadmissionpolicy,mutatingadmissionpolicy,validatingwebhookconfiguration -o name | grep -c essai
```

```text
validatingwebhookconfiguration.admissionregistration.k8s.io "essai-controle-configmaps" deleted
validatingadmissionpolicybinding.admissionregistration.k8s.io "essai-exige-cours" deleted
validatingadmissionpolicybinding.admissionregistration.k8s.io "essai-sans-hostpid" deleted
validatingadmissionpolicy.admissionregistration.k8s.io "essai-exige-cours" deleted
validatingadmissionpolicy.admissionregistration.k8s.io "essai-sans-hostpid" deleted
mutatingadmissionpolicybinding.admissionregistration.k8s.io "essai-pose-cours" deleted
mutatingadmissionpolicy.admissionregistration.k8s.io "essai-pose-cours" deleted
namespace "essai-admission" deleted
namespace "essai-temoin" deleted
0
```

No scratch object left. Then leave the machine and reset the lab.
`dsoxlab reset` replays the clean-up and then the lab preparation: you get
back exactly the starting state of the challenge. It asks you to confirm:
answer `y`.

```bash
exit
dsoxlab reset k8s-valider-et-modifier-a-l-admission
dsoxlab check k8s-valider-et-modifier-a-l-admission
```

```text
╭─ Result: k8s-valider-et-modifier-a-l-admission ─╮
│  0 / 100 pts                                    │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests                │
╰─────────────────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: unblock a namespace where no Pod can be
created any more, then have the API server itself set a default label there
and refuse privileged containers.

```bash
dsoxlab run k8s-valider-et-modifier-a-l-admission
dsoxlab challenge k8s-valider-et-modifier-a-l-admission
```
