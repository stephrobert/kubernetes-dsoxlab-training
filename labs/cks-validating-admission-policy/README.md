# Have the cluster refuse an object with a ValidatingAdmissionPolicy

The lesson shows how to write a ValidatingAdmissionPolicy in CEL, bind it to
namespaces and roll it out in `Audit`, `Warn` then `Deny`. This course adds
four cases it does not show: a policy without a binding that acts on nothing,
a policy on ConfigMaps rather than Pods, an object created before the binding
and refused only at its next change, and the error you get when reading a
missing field without `has()`.

You work in the `essai-vap` namespace, with a policy that requires an `equipe`
label on ConfigMaps. The challenge targets another namespace and another rule:
you will do it on your own, at the end.

Related page: [ValidatingAdmissionPolicy](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/validating-admission-policy/) (in French).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-validating-admission-policy
```

You are now logged into `k8s-cp.lab`, the node that drives the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on
22 November 2026, with Kubernetes v1.37.2.

## 📜 Exercise 1: a policy alone does nothing

Create the test namespace and a policy that requires the `equipe` label on any
ConfigMap created or changed. `has()` first checks that the object carries
labels, before looking for `equipe` among them. Then create a ConfigMap
without a label:

```bash
kubectl create namespace essai-vap; cat <<'YAML' | kubectl apply -f -
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: essai-etiquette-equipe
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: [v1]
        operations: [CREATE, UPDATE]
        resources: [configmaps]
  validations:
    - expression: 'has(object.metadata.labels) && "equipe" in object.metadata.labels'
      message: "une ConfigMap de essai-vap porte le label equipe"
YAML
kubectl create configmap sans-label -n essai-vap --from-literal=a=1
```

```text
namespace/essai-vap created
validatingadmissionpolicy.admissionregistration.k8s.io/essai-etiquette-equipe created
configmap/sans-label created
```

The policy is created, and so is the ConfigMap: a policy only says **what** to
check. As long as no binding says **where** to apply it, it acts on nothing,
and nothing warns you.

## 🔗 Exercise 2: the binding turns it on, for one namespace

Bind the policy to the `essai-vap` namespace only, in `Deny` mode, then create
a second ConfigMap without a label:

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: essai-etiquette-equipe
spec:
  policyName: essai-etiquette-equipe
  validationActions: [Deny]
  matchResources:
    namespaceSelector:
      matchLabels: {kubernetes.io/metadata.name: essai-vap}
YAML
sleep 3; kubectl create configmap sans-label-2 -n essai-vap --from-literal=a=1
```

```text
validatingadmissionpolicybinding.admissionregistration.k8s.io/essai-etiquette-equipe created
error: failed to create configmap: configmaps "sans-label-2" is forbidden: ValidatingAdmissionPolicy 'essai-etiquette-equipe' with binding 'essai-etiquette-equipe' denied request: une ConfigMap de essai-vap porte le label equipe
```

Refused, with the message of the policy. Now create a ConfigMap that carries
the label in `essai-vap`, and a ConfigMap without a label in `default`:

```bash
kubectl create configmap avec-label -n essai-vap --from-literal=a=1 --dry-run=client -o yaml | kubectl label --local -f - equipe=accueil -o yaml | kubectl apply -f -; kubectl create configmap ailleurs -n default --from-literal=a=1; kubectl delete configmap ailleurs -n default >/dev/null
```

```text
configmap/avec-label created
configmap/ailleurs created
```

Both pass: the first follows the rule, the second is outside the namespace
targeted by the binding. The `namespaceSelector` of the binding bounds the
effect of the policy.

## ⏳ Exercise 3: an object from before the binding

The ConfigMap `sans-label` from exercise 1 still exists, without a label. A
policy never goes back over existing objects: it judges what reaches the API
server. Change it, even with a mere annotation:

```bash
kubectl get configmap sans-label -n essai-vap -o name; kubectl annotate configmap sans-label -n essai-vap revue=faite 2>&1 | cut -c1-220
```

```text
configmap/sans-label
The configmaps "sans-label" is invalid: : ValidatingAdmissionPolicy 'essai-etiquette-equipe' with binding 'essai-etiquette-equipe' denied request: une ConfigMap de essai-vap porte le label equipe
```

Refused: the rule also covers `UPDATE`, and the ConfigMap does not follow it.
An old object therefore goes unnoticed until its next change, which then fails
for a reason its author did not cause. Before setting a binding to `Deny`,
look for existing objects that break the rule.

## ⚠️ Exercise 4: without has(), an error instead of a clear refusal

Replace the expression with a version without `has()`, then create a
ConfigMap with no label at all:

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: essai-etiquette-equipe
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: [v1]
        operations: [CREATE, UPDATE]
        resources: [configmaps]
  validations:
    - expression: '"equipe" in object.metadata.labels'
      message: "une ConfigMap de essai-vap porte le label equipe"
YAML
sleep 3; kubectl create configmap sans-label-3 -n essai-vap --from-literal=a=1 2>&1 | cut -c1-400
```

```text
validatingadmissionpolicy.admissionregistration.k8s.io/essai-etiquette-equipe configured
error: failed to create configmap: configmaps "sans-label-3" is forbidden: ValidatingAdmissionPolicy 'essai-etiquette-equipe' with binding 'essai-etiquette-equipe' denied request: expression '"equipe" in object.metadata.labels' resulted in error: no such key: labels
```

The ConfigMap is refused, but not by the message of the policy: the API
server could not **evaluate** the expression (`no such key: labels`), because
an object without labels has no `labels` field. With `failurePolicy: Fail`, an
evaluation error refuses the request. With `Ignore`, it would have let it
through. Guard every access to an optional field with `has()`.

## 🧹 Clean-up

Delete the binding, the policy, then the test namespace:

```bash
kubectl delete validatingadmissionpolicybinding essai-etiquette-equipe; kubectl delete validatingadmissionpolicy essai-etiquette-equipe; kubectl delete namespace essai-vap
```

```text
validatingadmissionpolicybinding.admissionregistration.k8s.io "essai-etiquette-equipe" deleted
validatingadmissionpolicy.admissionregistration.k8s.io "essai-etiquette-equipe" deleted
namespace "essai-vap" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cks-validating-admission-policy
dsoxlab check cks-validating-admission-policy
```

```text
╭─ Result: cks-validating-admission-policy ─╮
│  0 / 100 pts                              │
│  ░░░░░░░░░░░░░░░░░░░░  0/2 tests          │
╰───────────────────────────────────────────╯
```

0 out of 2: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: have the cluster refuse, in a single
namespace, the Pods whose image is not pinned by its digest.

```bash
dsoxlab run cks-validating-admission-policy
dsoxlab challenge cks-validating-admission-policy
```
