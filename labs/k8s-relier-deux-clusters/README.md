# Connect two clusters with ClusterMesh

The lesson prepares two Cilium clusters, connects them with ClusterMesh and
makes a Service global, served by both. Connecting the clusters and making
the Service global is the challenge of this lab: this course connects
nothing. It checks the conditions the lesson sets without checking them,
before the connection: distinct identities, Pod ranges that do not overlap, a
single certificate authority, an entry point that is reachable and signed by
that authority, and the state the CLI reports before any connection.

You work in a scratch directory, `~/essai-mesh`, without creating anything in
the clusters. The challenge is about the connection and the `echo` Service:
you will do it on your own, at the end.

Related page: [Connect two clusters with ClusterMesh](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/clustermesh/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-relier-deux-clusters
```

You are now connected to `ha-cp1.lab`, the only node of `cluster-1`. Your
kubeconfig knows both clusters, each through its context:

```bash
kubectl config get-contexts
```

```text
CURRENT   NAME        CLUSTER         AUTHINFO          NAMESPACE
*         cluster-1   k8s-cluster-1   admin-cluster-1
          cluster-2   k8s-cluster-2   admin-cluster-2
```

Every command of this course passes `--context`, so that there is no doubt
about the cluster being queried. The outputs shown were captured on these
machines on 22 November 2026 (Kubernetes v1.37.2, Cilium 1.20.5, `cilium` CLI
v0.20.3).

## 🪪 Exercise 1: two distinct identities

Each cluster of a mesh must carry a name and a numeric identifier of its own:
Cilium uses them to know which cluster each Pod and each security identity
belongs to. Read them in the Cilium configuration of each cluster:

```bash
for c in cluster-1 cluster-2; do echo "$c: $(kubectl --context $c -n kube-system get cm cilium-config -o jsonpath='{.data.cluster-name} id={.data.cluster-id}')"; done
```

```text
cluster-1: cluster-1 id=1
cluster-2: cluster-2 id=2
```

Names and identifiers differ. These values are set when Cilium is installed:
two clusters installed with the default values would carry the same name,
`default`, and the same identifier, and could not be connected as they are.

## 🗺️ Exercise 2: Pod ranges that do not overlap

A Pod of `cluster-1` must be able to reach a Pod of `cluster-2` by its
address: two Pods must therefore never have the same one. Read the block of
each node, then check that the two pools do not overlap. The pools,
`10.241.0.0/16` and `10.242.0.0/16`, are those of the `cluster-pool-ipv4-cidr`
key of `cilium-config`:

```bash
for c in cluster-1 cluster-2; do echo "$c: $(kubectl --context $c get ciliumnodes -o jsonpath='{range .items[*]}{.metadata.name} {.spec.ipam.podCIDRs}{end}')"; done
python3 -c 'import ipaddress as ip; print("recoupement :", ip.ip_network("10.241.0.0/16").overlaps(ip.ip_network("10.242.0.0/16")))'
```

```text
cluster-1: ha-cp1.lab ["10.241.0.0/24"]
cluster-2: ha-cp2.lab ["10.242.0.0/24"]
recoupement : False
```

Each node has its block in the pool of its cluster, and the pools do not
overlap (`recoupement` means overlap). Two clusters installed with Cilium's
default pool, `10.0.0.0/8`, would have the same one: two Pods, one on each
side, could get the same address.

## 🔐 Exercise 3: a single certificate authority

The agents of one cluster connect to the entry point of the other over TLS.
They only trust it if its certificate is signed by the authority they know.
The two clusters must therefore share Cilium's certificate authority, the
`cilium-ca` Secret. Keep the one of `cluster-1` in the scratch directory for
the next exercise, then compare the fingerprints of both:

```bash
mkdir -p ~/essai-mesh
kubectl --context cluster-1 -n kube-system get secret cilium-ca -o jsonpath='{.data.ca\.crt}' | base64 -d > ~/essai-mesh/ca-cluster-1.crt
for c in cluster-1 cluster-2; do echo "$c: $(kubectl --context $c -n kube-system get secret cilium-ca -o jsonpath='{.data.ca\.crt}' | base64 -d | openssl x509 -noout -fingerprint -sha256 | cut -c1-60)"; done
```

```text
cluster-1: sha256 Fingerprint=38:4E:B6:1D:33:AA:55:CC:76:E8:1F:3A:BD:AA
cluster-2: sha256 Fingerprint=38:4E:B6:1D:33:AA:55:CC:76:E8:1F:3A:BD:AA
```

The fingerprints are identical (the beginning is enough to compare): both
clusters have the same authority. Two clusters installed each on its own
would each have one, generated at installation.

## 🔌 Exercise 4: a reachable and signed entry point

Each cluster exposes its `clustermesh-apiserver`, the entry point the agents
of the other cluster query. Here, it is a NodePort Service. Read the one of
`cluster-2`, test its port from `ha-cp1`, then a neighbouring port where
nothing listens:

```bash
kubectl --context cluster-2 -n kube-system get svc clustermesh-apiserver
timeout 3 bash -c '</dev/tcp/10.10.50.19/32379'; echo "32379 code=$?"
timeout 3 bash -c '</dev/tcp/10.10.50.19/32380'; echo "32380 code=$?"
```

```text
NAME                    TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)          AGE
clustermesh-apiserver   NodePort   10.112.253.96   <none>        2379:32379/TCP   2m5s
32379 code=0
bash: connect: Connection refused
bash: line 1: /dev/tcp/10.10.50.19/32380: Connection refused
32380 code=1
```

Port `32379` of `ha-cp2` (`10.10.50.19`) accepts the connection, the
neighbouring port refuses it. Reachable does not yet mean trustworthy. Ask
`openssl` to check the certificate this entry point presents with the
authority of `cluster-1`:

```bash
openssl s_client -connect 10.10.50.19:32379 -CAfile ~/essai-mesh/ca-cluster-1.crt </dev/null 2>/dev/null | grep -E '^(subject|issuer)=|Verify return code'
```

```text
subject=CN = clustermesh-apiserver.kube-system.svc
issuer=CN = Cilium CA
Verify return code: 0 (ok)
```

The entry point of `cluster-2` presents a certificate issued by `Cilium CA`,
and `openssl` validates it with the authority of `cluster-1`: `Verify return
code: 0 (ok)`. This is exactly the check the agents of `cluster-1` will make
once the clusters are connected. With two different authorities, you would
read a non-zero verification code here.

## 📋 Exercise 5: the state before the connection

The `cilium` CLI sums up the mesh state of a cluster. Its default display is
made for the eye; for a script, ask for JSON (`-o json`) and keep the useful
fields with `jq`. The progress lines go to the error output, which
`2>/dev/null` discards:

```bash
cilium clustermesh status --context cluster-1 -o json 2>/dev/null | jq -c '{cluster: .access_information.cluster_name, adresse: .access_information.service_ips, port: .access_information.service_port, connectes: .connectivity.connected}'; echo "code=$?"
```

```text
{"cluster":"cluster-1","adresse":["10.10.50.18"],"port":32379,"connectes":{}}
code=0
```

The entry point of `cluster-1` is announced at the address of `ha-cp1`,
`10.10.50.18`, on port `32379`: this is the address the other cluster will
use. The field that matters is `connectes` (connected), an empty object: no
cluster is connected. Yet the command exits with **0**: a script cannot rely
on the exit code to know whether the clusters are connected, it must read
this field. The announced address is a node's, since the Service is a
NodePort: if that node goes away, the other cluster loses its entry point.

## 🧹 Clean-up

Delete the scratch directory, the only thing this course created:

```bash
rm -rf ~/essai-mesh; ls -d ~/essai-mesh
```

```text
ls: cannot access '/home/ansible/essai-mesh': No such file or directory
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the
clean-up and then the lab preparation: you get back exactly the starting state
of the challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-relier-deux-clusters
dsoxlab check k8s-relier-deux-clusters
```

```text
╭─ Result: k8s-relier-deux-clusters ─╮
│  0 / 100 pts                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests   │
╰────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for
you, untouched.

## 🎯 The challenge

Your turn, on your own this time: connect the two clusters, make their `echo`
Service global, and prove that a client of `cluster-1` gets answers from both
clusters.

```bash
dsoxlab run k8s-relier-deux-clusters
dsoxlab challenge k8s-relier-deux-clusters
```
