# Enforce rules with Gatekeeper

The lesson presents Gatekeeper: its installation, the ConstraintTemplate and
Constraint pair, the three modes `dryrun`, `warn` and `deny`, the audit of
existing resources and local tests with gator. This course has you perform
each of these steps on the cluster, with two scratch rules: no `hostPath`
volume, no `privileged` container.

You work in the `essai-gk` namespace and the `~/essai-gator` directory. The
challenge uses another rule and another namespace: you will do it on your
own, at the end.

Related page: [OPA Gatekeeper](https://www.stephane-robert.info/en/docs/devsecops/runtime/gatekeeper/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-imposer-des-regles-avec-gatekeeper
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm
cluster (the control plane). Your kubectl already targets it.

The outputs shown in this course were captured on this machine on
23 November 2026, with Kubernetes v1.37.2 and Gatekeeper v3.23.1.

## 📦 Exercise 1: install Gatekeeper

Install Gatekeeper from its release manifest, pinned by its tag, then wait
for its two Deployments:

```bash
kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/v3.23.1/deploy/gatekeeper.yaml | tail -2
kubectl -n gatekeeper-system rollout status deployment gatekeeper-controller-manager --timeout=300s
kubectl -n gatekeeper-system rollout status deployment gatekeeper-audit --timeout=300s
kubectl -n gatekeeper-system get pods
kubectl get validatingwebhookconfiguration gatekeeper-validating-webhook-configuration -o jsonpath='{range .webhooks[*]}{.name} {.failurePolicy}{"\n"}{end}'
```

```text
mutatingwebhookconfiguration.admissionregistration.k8s.io/gatekeeper-mutating-webhook-configuration created
validatingwebhookconfiguration.admissionregistration.k8s.io/gatekeeper-validating-webhook-configuration created
Waiting for deployment "gatekeeper-controller-manager" rollout to finish: 0 of 3 updated replicas are available...
Waiting for deployment "gatekeeper-controller-manager" rollout to finish: 1 of 3 updated replicas are available...
Waiting for deployment "gatekeeper-controller-manager" rollout to finish: 2 of 3 updated replicas are available...
deployment "gatekeeper-controller-manager" successfully rolled out
deployment "gatekeeper-audit" successfully rolled out
NAME                                             READY   STATUS    RESTARTS      AGE
gatekeeper-audit-75d6fc8fd4-ljr42                1/1     Running   2 (13s ago)   25s
gatekeeper-controller-manager-5f7bd474ff-9jpvh   1/1     Running   0             25s
gatekeeper-controller-manager-5f7bd474ff-kplxm   1/1     Running   0             25s
gatekeeper-controller-manager-5f7bd474ff-kzwgg   1/1     Running   0             25s
validation.gatekeeper.sh Ignore
check-ignore-label.gatekeeper.sh Fail
```

Three controllers (the admission webhook, highly available) and an audit Pod
run after 27 seconds. The audit Pod restarted while the webhook was
starting (once or twice depending on the run), then stayed stable. The main webhook, `validation.gatekeeper.sh`,
is set to `Ignore`: if Gatekeeper goes down, requests go through unchecked.

## 🔍 Exercise 2: a rule in dryrun, and what the audit says

Create the scratch namespace and a Pod that mounts the node's `/etc`
directory through a `hostPath` volume. Then write a ConstraintTemplate that
forbids these volumes, wait for the CRD it declares to be ready, and create
its Constraint in `dryrun` mode, limited to `essai-gk`. Gatekeeper creates
this CRD a few moments after the template: the `until` loop waits for it to
exist, then `kubectl wait` waits for it to be usable.

```bash
kubectl create namespace essai-gk
cat > hostpath-pod.yaml <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: essai-hote
spec:
  containers:
    - name: c
      image: busybox:1.37
      command: ["sleep", "3600"]
      volumeMounts:
        - name: etc-hote
          mountPath: /hote
  volumes:
    - name: etc-hote
      hostPath:
        path: /etc
YAML
kubectl -n essai-gk apply -f hostpath-pod.yaml
cat <<'YAML' | kubectl apply -f -
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: essaisanshostpath
spec:
  crd:
    spec:
      names:
        kind: EssaiSansHostPath
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package essaisanshostpath

        violation[{"msg": msg}] {
          volume := input.review.object.spec.volumes[_]
          volume.hostPath
          msg := sprintf("Volume hostPath '%v' interdit", [volume.name])
        }
YAML
until kubectl get crd essaisanshostpath.constraints.gatekeeper.sh >/dev/null 2>&1; do sleep 2; done
kubectl wait --for=condition=established crd/essaisanshostpath.constraints.gatekeeper.sh --timeout=60s
cat <<'YAML' | kubectl apply -f -
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: EssaiSansHostPath
metadata:
  name: essai-sans-hostpath
spec:
  enforcementAction: dryrun
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    namespaces: ["essai-gk"]
YAML
sleep 5; sed 's/essai-hote/essai-hote-2/' hostpath-pod.yaml | kubectl -n essai-gk apply -f -
```

```text
namespace/essai-gk created
pod/essai-hote created
constrainttemplate.templates.gatekeeper.sh/essaisanshostpath created
customresourcedefinition.apiextensions.k8s.io/essaisanshostpath.constraints.gatekeeper.sh condition met
essaisanshostpath.constraints.gatekeeper.sh/essai-sans-hostpath created
pod/essai-hote-2 created
```

The second Pod, created after the Constraint, still goes through: in
`dryrun`, Gatekeeper prevents nothing. Wait for an audit pass (once a
minute), then read the `status` of the Constraint:

```bash
sleep 70
kubectl get essaisanshostpath essai-sans-hostpath -o jsonpath='{range .status.violations[*]}{.enforcementAction} {.namespace}/{.name}: {.message}{"\n"}{end}'
kubectl get constraints
```

```text
dryrun essai-gk/essai-hote-2: Volume hostPath 'etc-hote' interdit
dryrun essai-gk/essai-hote: Volume hostPath 'etc-hote' interdit
NAME                  ENFORCEMENT-ACTION   TOTAL-VIOLATIONS
essai-sans-hostpath   dryrun               2
```

The audit reports both Pods, including `essai-hote`, created **before** the
rule: admission never saw it. This report is what you read before switching
a rule to `deny`, to know what it would break.

## 🚫 Exercise 3: switch the rule to deny

Change the mode of the Constraint, without touching the template, then try
to create a third Pod with a `hostPath` volume:

```bash
kubectl patch essaisanshostpath essai-sans-hostpath --type=merge -p '{"spec":{"enforcementAction":"deny"}}'
sleep 5; sed 's/essai-hote/essai-hote-3/' hostpath-pod.yaml | kubectl -n essai-gk apply -f -
kubectl -n essai-gk get pods
```

```text
essaisanshostpath.constraints.gatekeeper.sh/essai-sans-hostpath patched
Error from server (Forbidden): error when creating "STDIN": admission webhook "validation.gatekeeper.sh" denied the request: [essai-sans-hostpath] Volume hostPath 'etc-hote' interdit
NAME           READY   STATUS    RESTARTS   AGE
essai-hote     1/1     Running   0          69s
essai-hote-2   1/1     Running   0          61s
```

The third Pod is refused, and the message names the Constraint in brackets.
The two Pods already created keep running: `deny` acts at admission, it
deletes nothing.

## ⚠️ Exercise 4: a rule in warn

Create a second rule, aimed at `privileged` containers, in `warn` mode. Then
submit a privileged Pod with `--dry-run=server`: the request goes through the
whole admission chain, but nothing is stored.

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: essaisansprivileged
spec:
  crd:
    spec:
      names:
        kind: EssaiSansPrivileged
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package essaisansprivileged

        violation[{"msg": msg}] {
          c := input.review.object.spec.containers[_]
          c.securityContext.privileged == true
          msg := sprintf("Conteneur '%v' en mode privileged", [c.name])
        }
YAML
until kubectl get crd essaisansprivileged.constraints.gatekeeper.sh >/dev/null 2>&1; do sleep 2; done
kubectl wait --for=condition=established crd/essaisansprivileged.constraints.gatekeeper.sh --timeout=60s
cat <<'YAML' | kubectl apply -f -
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: EssaiSansPrivileged
metadata:
  name: essai-sans-privileged
spec:
  enforcementAction: warn
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    namespaces: ["essai-gk"]
YAML
sleep 5; kubectl -n essai-gk run essai-priv --image=busybox:1.37 --restart=Never --dry-run=server --overrides='{"spec":{"containers":[{"name":"essai-priv","image":"busybox:1.37","command":["sleep","60"],"securityContext":{"privileged":true}}]}}'
```

```text
constrainttemplate.templates.gatekeeper.sh/essaisansprivileged created
customresourcedefinition.apiextensions.k8s.io/essaisansprivileged.constraints.gatekeeper.sh condition met
essaisansprivileged.constraints.gatekeeper.sh/essai-sans-privileged created
Warning: [essai-sans-privileged] Conteneur 'essai-priv' en mode privileged
pod/essai-priv created (server dry run)
```

The Pod is accepted, with a warning that carries the same text as a refusal.
The `warn` mode warns without blocking: it is the step where teams discover
the rule before it refuses.

## 🧪 Exercise 5: test a rule outside the cluster with gator

gator, the Gatekeeper CLI, evaluates a rule against files, without a
cluster. Download it, check its checksum, then write the template, a
Constraint and two Pods in a working directory:

```bash
mkdir -p ~/essai-gator && cd ~/essai-gator
curl -fsSLO https://github.com/open-policy-agent/gatekeeper/releases/download/v3.23.1/gator-v3.23.1-linux-amd64.tar.gz
curl -fsSLO https://github.com/open-policy-agent/gatekeeper/releases/download/v3.23.1/sha256sums.txt
grep gator-v3.23.1-linux-amd64.tar.gz sha256sums.txt | sed 's#\./##' | sha256sum -c -
tar xzf gator-v3.23.1-linux-amd64.tar.gz gator
cat > template.yaml <<'YAML'
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: essaisanshostpath
spec:
  crd:
    spec:
      names:
        kind: EssaiSansHostPath
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package essaisanshostpath

        violation[{"msg": msg}] {
          volume := input.review.object.spec.volumes[_]
          volume.hostPath
          msg := sprintf("Volume hostPath '%v' interdit", [volume.name])
        }
YAML
cat > constraint.yaml <<'YAML'
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: EssaiSansHostPath
metadata:
  name: essai-sans-hostpath
spec:
  enforcementAction: deny
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
YAML
cp ~/hostpath-pod.yaml pod-hostpath.yaml
cat > pod-simple.yaml <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: essai-simple
spec:
  containers:
    - name: c
      image: busybox:1.37
YAML
```

```text
gator-v3.23.1-linux-amd64.tar.gz: OK
```

`gator test` evaluates an object against the template and its Constraint.
Run it on each of the two Pods:

```bash
./gator test --filename template.yaml --filename constraint.yaml --filename pod-hostpath.yaml; echo "code=$?"
./gator test --filename template.yaml --filename constraint.yaml --filename pod-simple.yaml; echo "code=$?"
```

```text
v1/Pod essai-hote: ["essai-sans-hostpath"] Message: "Volume hostPath 'etc-hote' interdit"
code=1
code=0
```

The Pod with a `hostPath` volume exits with code 1 and the violation, the
simple Pod with code 0 and no output. A pipeline can stop on that code.
`gator verify` goes further: it runs a suite of cases, each with its
expected result.

```bash
cat > suite.yaml <<'YAML'
kind: Suite
apiVersion: test.gatekeeper.sh/v1alpha1
tests:
  - name: sans-hostpath
    template: template.yaml
    constraint: constraint.yaml
    cases:
      - name: pod-hostpath-refuse
        object: pod-hostpath.yaml
        assertions:
          - violations: yes
      - name: pod-simple-passe
        object: pod-simple.yaml
        assertions:
          - violations: no
YAML
./gator verify suite.yaml
sed -i 's/violations: no/violations: yes/' suite.yaml
./gator verify suite.yaml
cd ~
```

```text
ok	suite.yaml	0.006s
PASS
    --- FAIL: pod-simple-passe	(0.002s)
        unexpected number of violations: got 0 violations but want at least 1: got messages []
--- FAIL: sans-hostpath	(0.006s)
FAIL	suite.yaml	0.006s
FAIL
Error: FAIL
```

The suite passes. Then make one expectation wrong (the simple Pod "should"
be refused): gator names the failing case and says why. That is what makes a
gator suite a real test, not a mere review.

## 🧹 Clean-up

Delete the Constraints, then the templates (deleting them removes the CRDs
they created), the scratch namespace, and finally Gatekeeper itself with the
same manifest as for the installation. The last commands count what is left
of Gatekeeper:

```bash
kubectl delete essaisanshostpath essai-sans-hostpath
kubectl delete essaisansprivileged essai-sans-privileged
kubectl delete constrainttemplate essaisanshostpath essaisansprivileged
kubectl delete namespace essai-gk --wait=true --timeout=120s
kubectl delete -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/v3.23.1/deploy/gatekeeper.yaml --wait=true | tail -2
rm -rf ~/essai-gator ~/hostpath-pod.yaml
kubectl get crd -o name | grep -c gatekeeper.sh
kubectl get validatingwebhookconfiguration,mutatingwebhookconfiguration -o name | grep -c gatekeeper
```

```text
essaisanshostpath.constraints.gatekeeper.sh "essai-sans-hostpath" deleted
essaisansprivileged.constraints.gatekeeper.sh "essai-sans-privileged" deleted
constrainttemplate.templates.gatekeeper.sh "essaisanshostpath" deleted
constrainttemplate.templates.gatekeeper.sh "essaisansprivileged" deleted
namespace "essai-gk" deleted
mutatingwebhookconfiguration.admissionregistration.k8s.io "gatekeeper-mutating-webhook-configuration" deleted
validatingwebhookconfiguration.admissionregistration.k8s.io "gatekeeper-validating-webhook-configuration" deleted
0
0
```

No Gatekeeper CRD or webhook left. Then leave the machine and reset the lab.
`dsoxlab reset` replays the clean-up and then the lab preparation: you get
back exactly the starting state of the challenge. It asks you to confirm:
answer `y`.

```bash
exit
dsoxlab reset k8s-imposer-des-regles-avec-gatekeeper
dsoxlab check k8s-imposer-des-regles-avec-gatekeeper
```

```text
╭─ Result: k8s-imposer-des-regles-avec-gatekeeper ─╮
│  0 / 100 pts                                     │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests                 │
╰──────────────────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: install Gatekeeper, make it refuse in a
namespace the images that do not come from the allowed registry, and read in
its audit the Pod that was running before the rule.

```bash
dsoxlab run k8s-imposer-des-regles-avec-gatekeeper
dsoxlab challenge k8s-imposer-des-regles-avec-gatekeeper
```
