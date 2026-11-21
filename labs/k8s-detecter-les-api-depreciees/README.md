# Detect and migrate removed APIs

The lesson shows how Kubernetes removes API versions, and how to find the
manifests that still use them. This course has you migrate two scratch
manifests, on types that neither the lesson nor the challenge uses, and adds
cases they do not show: reading the versions served per group, the message
for a removed version, a migration that only changes the version, and a
field that changed shape.

You work in a scratch directory, `~/essai-api`, and a scratch namespace,
`essai-api`, with a Role `lecteur` ("reader") and an EndpointSlice `repere`
("marker"). The challenge is about another repository of manifests: you will
do it on your own, at the end.

Related page (in French): [Dépréciations des API Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/api-deprecations/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-detecter-les-api-depreciees
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: the versions the API serves today

List the versions served for three API groups:

```bash
kubectl api-versions | grep -E '^(rbac|discovery|scheduling)'
```

```text
discovery.k8s.io/v1
rbac.authorization.k8s.io/v1
scheduling.k8s.io/v1
```

A single version per group: `v1`. The `v1beta1` versions of these groups were
removed. To know which version a type is served under, ask per group:

```bash
kubectl api-resources --api-group=discovery.k8s.io; kubectl api-resources --api-group=rbac.authorization.k8s.io
```

```text
NAME             SHORTNAMES   APIVERSION            NAMESPACED   KIND
endpointslices                discovery.k8s.io/v1   true         EndpointSlice
NAME                  SHORTNAMES   APIVERSION                     NAMESPACED   KIND
clusterrolebindings                rbac.authorization.k8s.io/v1   false        ClusterRoleBinding
clusterroles                       rbac.authorization.k8s.io/v1   false        ClusterRole
rolebindings                       rbac.authorization.k8s.io/v1   true         RoleBinding
roles                              rbac.authorization.k8s.io/v1   true         Role
```

The `APIVERSION` column gives the version to write in a manifest. That is the
reference: not a documentation page, not an old manifest, but what the
cluster serves.

## ⛔ Exercise 2: a removed version, and what the API says

Write a Role in `rbac.authorization.k8s.io/v1beta1`, and ask the API server
whether it accepts it, without creating anything (`--dry-run=server`):

```bash
kubectl create namespace essai-api; mkdir -p ~/essai-api; cat > ~/essai-api/role.yaml <<'YAML'
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: Role
metadata:
  name: lecteur
  namespace: essai-api
rules:
  - apiGroups: [""]
    resources: [pods]
    verbs: [get, list]
YAML
kubectl apply --dry-run=server -f ~/essai-api/role.yaml
```

```text
namespace/essai-api created
error: resource mapping not found for name: "lecteur" namespace: "essai-api" from "/home/ansible/essai-api/role.yaml": no matches for kind "Role" in version "rbac.authorization.k8s.io/v1beta1"
ensure CRDs are installed first
```

`no matches for kind "Role" in version "rbac.authorization.k8s.io/v1beta1"`.
The API no longer knows this type and version pair. The second line mentions
CRDs, because the same message is used for an unknown type: here, that is not
the problem.

## ✔️ Exercise 3: a migration that only changes the version

For a Role, nothing else changed between `v1beta1` and `v1`. Replace the
version, and ask again:

```bash
sed -i 's#rbac.authorization.k8s.io/v1beta1#rbac.authorization.k8s.io/v1#' ~/essai-api/role.yaml; kubectl apply --dry-run=server -f ~/essai-api/role.yaml
```

```text
role.rbac.authorization.k8s.io/lecteur created (server dry run)
```

Accepted. For many types, migrating comes down to the `apiVersion` line. That
is not always the case.

## 🔀 Exercise 4: a field that changed shape

In `discovery.k8s.io/v1beta1`, an EndpointSlice stored each address's node in
a `topology` field. Write an EndpointSlice in `v1`, but with that old field:

```bash
cat > ~/essai-api/repere.yaml <<'YAML'
apiVersion: discovery.k8s.io/v1
kind: EndpointSlice
metadata:
  name: repere
  namespace: essai-api
addressType: IPv4
endpoints:
  - addresses: [10.244.0.50]
    topology:
      kubernetes.io/hostname: k8s-w1.lab
ports:
  - port: 80
YAML
kubectl apply --dry-run=server -f ~/essai-api/repere.yaml
```

```text
Error from server (BadRequest): error when creating "/home/ansible/essai-api/repere.yaml": EndpointSlice in version "v1" cannot be handled as a EndpointSlice: strict decoding error: unknown field "endpoints[0].topology"
```

The version passes, the field does not: `unknown field
"endpoints[0].topology"`. The API's strict check refuses a field it does not
know, instead of ignoring it. Ask which fields version `v1` expects:

```bash
kubectl explain endpointslice.endpoints --api-version=discovery.k8s.io/v1 | grep -E '^  [a-zA-Z]+' 
```

```text
  addresses	<[]string> -required-
  conditions	<EndpointConditions>
  deprecatedTopology	<map[string]string>
  hints	<EndpointHints>
  hostname	<string>
  nodeName	<string>
  targetRef	<ObjectReference>
  zone	<string>
```

The node now has its own field, `nodeName`, and the old `topology` became
`deprecatedTopology`. Fix the manifest and ask again:

```bash
sed -i 's#    topology:#    nodeName: k8s-w1.lab#; /kubernetes.io\/hostname/d' ~/essai-api/repere.yaml; sed -n '/endpoints:/,/ports:/p' ~/essai-api/repere.yaml; kubectl apply --dry-run=server -f ~/essai-api/repere.yaml
```

```text
endpoints:
  - addresses: [10.244.0.50]
    nodeName: k8s-w1.lab
ports:
endpointslice.discovery.k8s.io/repere created (server dry run)
```

Accepted. Changing the version is not always enough: read the error to the
end, then `kubectl explain` on the target version.

## 🧹 Clean-up

Delete the namespace and the scratch directory:

```bash
kubectl delete namespace essai-api; rm -rf ~/essai-api
```

```text
namespace "essai-api" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-detecter-les-api-depreciees
dsoxlab check k8s-detecter-les-api-depreciees
```

```text
╭─ Result: k8s-detecter-les-api-depreciees ─╮
│  0 / 100 pts                              │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests          │
╰───────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a repository of old manifests, to sort and
migrate without changing anything they describe.

```bash
dsoxlab run k8s-detecter-les-api-depreciees
dsoxlab challenge k8s-detecter-les-api-depreciees
```
