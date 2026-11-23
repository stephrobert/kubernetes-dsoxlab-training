# Prepare a Cilium installation without kube-proxy

The lesson installs a cluster where Cilium replaces kube-proxy: an init
without the kube-proxy phase, the workers joined, `helm install`, then three
proofs. Building that cluster is the challenge of this lab, so this course
builds nothing. It prepares the choices made **before** the installation,
which cannot be fixed afterwards: checking that an init really skips
kube-proxy, choosing a Pod pool that overlaps nothing, reading what the chart
will write, and seeing what happens when `k8sServiceHost` is forgotten.

You work in a scratch directory, `~/essai-cilium`, with a fictitious cluster
`essai-reseau` and a Pod pool `10.250.0.0/16`. The challenge uses another pool
and a real cluster: you will do it on your own, at the end.

Related page: [Install Cilium without kube-proxy and choose its IPAM](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/cilium/) (in French).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-installer-cilium-sans-kube-proxy
```

You are now connected to `net-cp.lab`, the future control plane. The three
`net-*` nodes are ready (kubeadm, kubelet and kubectl 1.37, Helm 4.3.2), but
no cluster exists. Create the scratch directory:

```bash
mkdir -p ~/essai-cilium && cd ~/essai-cilium
```

The outputs shown in this course were captured on this machine on
22 November 2026 (kubeadm v1.37.2, Helm v4.3.2, kernel 6.8).

## 🧪 Exercise 1: check that an init skips kube-proxy, without creating anything

`kubeadm init --dry-run` runs every phase of an init, but writes its files to
a temporary directory and starts nothing. It is the way to check a command
before running it for real. Write a scratch configuration, then run two dry
inits, with and without `--skip-phases=addon/kube-proxy`:

```bash
cat > essai-init.yaml <<'YAML'
apiVersion: kubeadm.k8s.io/v1beta4
kind: ClusterConfiguration
clusterName: essai-reseau
networking:
  podSubnet: 10.250.0.0/16
YAML
sudo kubeadm init --config essai-init.yaml --dry-run > avec.txt 2>&1
sudo kubeadm init --config essai-init.yaml --dry-run --skip-phases=addon/kube-proxy > sans.txt 2>&1
grep '\[addons\]' avec.txt sans.txt
grep -c kube-proxy avec.txt sans.txt
```

```text
avec.txt:[addons] Applied essential addon: CoreDNS
avec.txt:[addons] Applied essential addon: kube-proxy
sans.txt:[addons] Applied essential addon: CoreDNS
avec.txt:23
sans.txt:0
```

Without the option, the init would install the `kube-proxy` addon, and its
name appears 23 times in the output, with the objects the addon would create
(a service account, a Role, a RoleBinding…). With the option, it does not
appear once. You know before running the init that the cluster will be born
without kube-proxy.

## 🗺️ Exercise 2: choose a Pod pool that overlaps nothing

The lesson says to choose a pool that overlaps neither the node network nor
the Service network. You still have to know those two networks. The Service
network is the one kubeadm sets by default, and the node network is read on
the machine's interface:

```bash
kubeadm config print init-defaults | grep serviceSubnet
ip -4 -o addr show enp1s0 | awk '{print $4}'
```

```text
  serviceSubnet: 10.96.0.0/12
10.10.50.14/24
```

Services take their addresses from `10.96.0.0/12` (from `10.96.0.0` to
`10.111.255.255`), and the nodes are in `10.10.50.0/24`. Test three candidate
pools with Python's `ipaddress` module, which can tell whether two networks
overlap:

```bash
python3 -c '
import ipaddress as ip
noeuds, services = ip.ip_network("10.10.50.0/24"), ip.ip_network("10.96.0.0/12")
for pool in ("10.0.0.0/8", "10.100.0.0/16", "10.250.0.0/16"):
    p = ip.ip_network(pool)
    print(pool, "noeuds:", p.overlaps(noeuds), "services:", p.overlaps(services))
'
```

```text
10.0.0.0/8 noeuds: True services: True
10.100.0.0/16 noeuds: False services: True
10.250.0.0/16 noeuds: False services: False
```

Cilium's default pool, `10.0.0.0/8`, overlaps both (`noeuds` means nodes).
`10.100.0.0/16` looks safe, but it falls inside the Service network: a Pod
could get the address of a Service. Only `10.250.0.0/16` overlaps nothing.

## 📄 Exercise 3: read what the chart will write

`helm template` produces the chart's manifests without sending anything to
the cluster. It does not even need a cluster. Declare the chart repository,
then render the chart with the scratch pool and `/26` blocks per node:

```bash
helm repo add cilium https://helm.cilium.io
helm template essai cilium/cilium --version 1.20.5 --namespace kube-system \
  --set kubeProxyReplacement=true \
  --set k8sServiceHost=10.10.50.14 --set k8sServicePort=6443 \
  --set ipam.mode=cluster-pool \
  --set 'ipam.operator.clusterPoolIPv4PodCIDRList={10.250.0.0/16}' \
  --set ipam.operator.clusterPoolIPv4MaskSize=26 > rendu.yaml
grep -E '^  (kube-proxy-replacement|ipam|cluster-pool-ipv4-cidr|cluster-pool-ipv4-mask-size):' rendu.yaml
```

```text
"cilium" has been added to your repositories
  kube-proxy-replacement: "true"
  ipam: "cluster-pool"
  cluster-pool-ipv4-cidr: "10.250.0.0/16"
  cluster-pool-ipv4-mask-size: "26"
```

These four lines come from the `cilium-config` ConfigMap, the one the agent
and the operator read at startup. The Helm value names become lowercase keys
with dashes: these are the names under which you will find them on an
installed cluster.

## 🔢 Exercise 4: a per-node block large enough

The per-node mask cannot be changed after the installation. Work out what the
`/26` of the previous exercise gives, then compare it with the number of Pods
a kubelet accepts by default:

```bash
python3 -c 'print("/16 en /26 :", 2**(26-16), "noeuds,", 2**(32-26)-2, "adresses par noeud")'
kubelet --help 2>/dev/null | grep -o -- '--max-pods int32 .*(default 110)' | tr -s ' '
```

```text
/16 en /26 : 1024 noeuds, 62 adresses par noeud
--max-pods int32 Number of Pods that can run on this Kubelet. (default 110)
```

A `/26` gives 1024 nodes and 62 addresses per node, while a kubelet accepts
110 Pods by default. On a busy node, the 63rd Pod would get no address while
the kubelet still accepts it. With a `/24` (254 addresses), the kubelet sets
the limit. The `/26` only fits if you also lower `maxPods`.

## 🔌 Exercise 5: what `k8sServiceHost` changes

Without kube-proxy, the Cilium agent cannot reach the API server through the
`kubernetes` Service, since nobody serves it yet. Render the chart a second
time, forgetting `k8sServiceHost` and `k8sServicePort`, and count the
containers that receive the API server address:

```bash
helm template essai cilium/cilium --version 1.20.5 --namespace kube-system \
  --set kubeProxyReplacement=true > oubli.yaml
grep -c 'name: KUBERNETES_SERVICE_HOST$' rendu.yaml oubli.yaml
grep -m1 -A1 'name: KUBERNETES_SERVICE_HOST$' rendu.yaml
```

```text
rendu.yaml:5
oubli.yaml:0
        - name: KUBERNETES_SERVICE_HOST
          value: "10.10.50.14"
```

With the value, five containers (the agent and two of its init containers,
the operator, the Envoy proxy) receive the `KUBERNETES_SERVICE_HOST`
variable, which replaces the address of the `kubernetes` Service. Without it,
Helm renders the chart without any error, and the variable no longer exists
anywhere: nothing warns you before the installation. The agent would then
look for the API server through a Service address that nobody serves.

## 🧹 Clean-up

Remove the scratch directory, the temporary files of the dry inits and the
chart repository declared in exercise 3:

```bash
cd ~ && rm -rf ~/essai-cilium && sudo rm -rf /etc/kubernetes/tmp
helm repo remove cilium
sudo ls /etc/kubernetes
```

```text
"cilium" has been removed from your repositories
manifests
pki
```

Only the two empty starting directories are left in `/etc/kubernetes`. Then
leave the machine and reset the lab. `dsoxlab reset` replays the clean-up and
then the lab preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-installer-cilium-sans-kube-proxy
dsoxlab check k8s-installer-cilium-sans-kube-proxy
```

```text
╭─ Result: k8s-installer-cilium-sans-kube-proxy ─╮
│  0 / 100 pts                                   │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests               │
╰────────────────────────────────────────────────╯
```

0 out of 6: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: build the cluster on the three nodes,
without kube-proxy, with Cilium in its place and the address pool chosen by
the team, then prove that a Service is served by Cilium.

```bash
dsoxlab run k8s-installer-cilium-sans-kube-proxy
dsoxlab challenge k8s-installer-cilium-sans-kube-proxy
```
