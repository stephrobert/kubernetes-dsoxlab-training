# Partition three tiers with ingress and egress NetworkPolicy

The lesson shows NetworkPolicies that filter Pods' incoming and outgoing
traffic. This course focuses on outgoing traffic (egress), measured port by
port, and adds cases the lesson does not show: a port range with `endPort`, an
egress opened to a Service's address that does not work, a port allowed to
any destination, and an egress to a Pod in another namespace.

You work in a scratch namespace, `essai-sortie`, with a server `ports` that
listens on several ports and a client `poste` ("workstation"), then in a
second namespace, `essai-voisin`. The challenge is about other objects: you
will do it on your own, at the end.

Related page: [Network Policies](https://www.stephane-robert.info/en/docs/devsecops/runtime/network-policies/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-networkpolicy-ingress-egress
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it. The Pod network is
provided by Calico, which enforces NetworkPolicies.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

Create the namespace, the server and the client. The `ports` server (agnhost
image, `porter` mode) listens on ports 8000, 8050, 8099 and 9000. A Service
exposes it on port 80, forwarded to 8000:

```bash
kubectl create namespace essai-sortie
kubectl run ports --image=registry.k8s.io/e2e-test-images/agnhost:2.53 -n essai-sortie --labels=app=ports --env=SERVE_PORT_8000=a --env=SERVE_PORT_8050=b --env=SERVE_PORT_8099=c --env=SERVE_PORT_9000=d -- porter; kubectl expose pod ports --port=80 --target-port=8000 -n essai-sortie; kubectl run poste --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-sortie --labels=app=poste -- sleep 3600; kubectl wait --for=condition=Ready pod --all -n essai-sortie --timeout=120s
```

```text
namespace/essai-sortie created
pod/ports created
service/ports exposed
pod/poste created
pod/ports condition met
pod/poste condition met
```

Each test in this course runs `nc -z` from `poste` to the `ports` Pod's
address, on each port, with a 3-second timeout. `ouvert` ("open") means the
connection succeeded, `ferme` ("closed") means it failed. With no policy,
everything goes through:

```bash
IP=$(kubectl get pod ports -n essai-sortie -o jsonpath='{.status.podIP}'); for p in 8000 8050 8099 9000; do printf '%-5s -> ' $p; kubectl exec poste -n essai-sortie -- nc -z -w 3 $IP $p >/dev/null 2>&1 && echo ouvert || echo ferme; done
```

```text
8000  -> ouvert
8050  -> ouvert
8099  -> ouvert
9000  -> ouvert
```

## 🎚️ Exercise 1: a port range

An egress policy applies to the Pod that sends, here `poste`. Allow its
outgoing traffic to `ports`, on the range 8000 to 8050, with `port` and
`endPort`:

```bash
cat <<'YAML' | kubectl apply -n essai-sortie -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: poste-sortie
spec:
  podSelector:
    matchLabels: {app: poste}
  policyTypes: [Egress]
  egress:
    - to:
        - podSelector:
            matchLabels: {app: ports}
      ports:
        - protocol: TCP
          port: 8000
          endPort: 8050
YAML
```

```text
sleep 5
networkpolicy.networking.k8s.io/poste-sortie created
```

```bash
IP=$(kubectl get pod ports -n essai-sortie -o jsonpath='{.status.podIP}'); for p in 8000 8050 8099 9000; do printf '%-5s -> ' $p; kubectl exec poste -n essai-sortie -- nc -z -w 3 $IP $p >/dev/null 2>&1 && echo ouvert || echo ferme; done
```

```text
8000  -> ouvert
8050  -> ouvert
8099  -> ferme
9000  -> ferme
```

8000 and 8050 go through: both bounds are included in the range. 8099 and
9000 are blocked. As soon as an `Egress` policy targets a Pod, any outgoing
traffic it does not allow is denied, including to the cluster's DNS. The
tests therefore use the Pod's address rather than its name.

## 🎯 Exercise 2: open the egress to the Service's address

A tempting idea: allow outgoing traffic to the Service's address, with a
`/32` `ipBlock`. The command reads that address, writes it into the policy,
then calls the Service on its port 80:

```bash
SVC=$(kubectl get service ports -n essai-sortie -o jsonpath='{.spec.clusterIP}'); echo "Service : $SVC"; cat <<YAML | kubectl apply -n essai-sortie -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: poste-sortie
spec:
  podSelector:
    matchLabels: {app: poste}
  policyTypes: [Egress]
  egress:
    - to:
        - ipBlock: {cidr: $SVC/32}
      ports:
        - {protocol: TCP, port: 8000}
YAML
sleep 5; kubectl exec poste -n essai-sortie -- nc -z -w 3 $SVC 80; echo "vers le Service : code $?"
```

```text
Service : 10.96.156.194
networkpolicy.networking.k8s.io/poste-sortie configured
command terminated with exit code 1
vers le Service : code 1
```

Denied, although the policy targets exactly the address being called. A
Service's address is only a step: before the packet leaves the node, it is
replaced by the address of a Pod behind the Service. See which one:

```bash
kubectl get endpointslices -n essai-sortie -l kubernetes.io/service-name=ports -o jsonpath='{.items[0].endpoints[0].addresses[0]}{"\n"}'
```

```text
10.244.38.73
```

Calico compares the policy with this Pod address, on port 8000, not with the
Service's. A policy is therefore written towards Pods, with `podSelector`, as
in exercise 1, and never towards a Service's address.

## 🌐 Exercise 3: a port to any destination

An `egress` rule without a `to` field applies to every destination. Allow
only port 9000, to anywhere:

```bash
cat <<'YAML' | kubectl apply -n essai-sortie -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: poste-sortie
spec:
  podSelector:
    matchLabels: {app: poste}
  policyTypes: [Egress]
  egress:
    - ports:
        - {protocol: TCP, port: 9000}
YAML
```

```text
sleep 5
networkpolicy.networking.k8s.io/poste-sortie configured
```

```bash
IP=$(kubectl get pod ports -n essai-sortie -o jsonpath='{.status.podIP}'); for p in 8000 9000; do printf '%-5s -> ' $p; kubectl exec poste -n essai-sortie -- nc -z -w 3 $IP $p >/dev/null 2>&1 && echo ouvert || echo ferme; done
```

```text
8000  -> ferme
9000  -> ouvert
```

9000 goes through, 8000 does not: the range from exercise 1 is gone, because
the policy was replaced (same name, `configured`).

## 🏘️ Exercise 4: an egress to another namespace

Create a second namespace with a `voisin` ("neighbour") server:

```bash
kubectl create namespace essai-voisin; kubectl run voisin --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb -n essai-voisin --labels=app=voisin; kubectl wait --for=condition=Ready pod/voisin -n essai-voisin --timeout=120s
```

```text
namespace/essai-voisin created
pod/voisin created
pod/voisin condition met
```

Allow outgoing traffic to the `app=voisin` Pod of the `essai-voisin`
namespace. The `namespaceSelector` and the `podSelector` are in the same item
of the `to` list (a single dash): both conditions must be true. Every
namespace automatically carries the `kubernetes.io/metadata.name` label:

```bash
cat <<'YAML' | kubectl apply -n essai-sortie -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: poste-sortie
spec:
  podSelector:
    matchLabels: {app: poste}
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector:
            matchLabels: {kubernetes.io/metadata.name: essai-voisin}
          podSelector:
            matchLabels: {app: voisin}
      ports:
        - {protocol: TCP, port: 80}
YAML
```

```text
sleep 5; V=$(kubectl get pod voisin -n essai-voisin -o jsonpath='{.status.podIP}'); kubectl exec poste -n essai-sortie -- nc -z -w 3 $V 80; echo "vers voisin : code $?"
networkpolicy.networking.k8s.io/poste-sortie configured
vers voisin : code 0
```

The connection goes through. Change the label of the neighbour Pod and try
again:

```bash
kubectl label pod voisin -n essai-voisin app=autre --overwrite; sleep 5; V=$(kubectl get pod voisin -n essai-voisin -o jsonpath='{.status.podIP}'); kubectl exec poste -n essai-sortie -- nc -z -w 3 $V 80; echo "vers voisin relabellisé : code $?"
```

```text
pod/voisin labeled
command terminated with exit code 1
vers voisin relabellisé : code 1
```

Denied: the namespace still matches, but the Pod no longer does. According to
the specification, with two dashes (`- namespaceSelector` then
`- podSelector`), the two conditions would have become two separate
permissions, and the second one would have targeted the `app=voisin` Pods of
the policy's own namespace. One dash too many or too few changes the meaning
of the rule.

## 🧹 Clean-up

Delete the two scratch namespaces:

```bash
kubectl delete namespace essai-sortie essai-voisin
```

```text
namespace "essai-sortie" deleted
namespace "essai-voisin" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset ckad-networkpolicy-ingress-egress
dsoxlab check ckad-networkpolicy-ingress-egress
```

```text
╭─ Result: ckad-networkpolicy-ingress-egress ─╮
│  0 / 100 pts                                │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests            │
╰─────────────────────────────────────────────╯
```

0 out of 6: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: three tiers to partition, for incoming and
outgoing traffic.

```bash
dsoxlab run ckad-networkpolicy-ingress-egress
dsoxlab challenge ckad-networkpolicy-ingress-egress
```
