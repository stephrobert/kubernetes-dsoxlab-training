# Close network access to a worker without cutting the cluster off

The lesson shows how to write an nftables table with a `drop` policy that only
lets the Kubernetes flows through. This course adds what to do **before**
loading it: see the tables kube-proxy and Calico have already set up, get a
badly written rule refused, and **count** the traffic arriving on a port
without blocking anything, to know what to leave open.

You work on `k8s-w1.lab`, over `ssh` from the control plane. The test table of
this course **counts** packets, it drops none: you do not risk cutting the
node off. The challenge targets another node: you will do it on your own, at
the end.

Related page: [Harden the nodes of a Kubernetes cluster](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/durcir-les-noeuds/) (in French).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-fermer-l-acces-reseau-au-noeud
```

You are now logged into `k8s-cp.lab`, the node that drives the kubeadm cluster
(the control plane). Your kubectl already targets it, and `ssh` reaches the
workers.

The outputs shown in this course were recorded on this machine on
22 November 2026, with Kubernetes v1.37.2, Ubuntu 24.04 and nftables 1.0.9.

## 🗂️ Exercise 1: what is already in place

A Kubernetes node is never blank on the firewall side. List the nftables
tables of `k8s-w1.lab`:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo nft list tables'
```

```text
table ip mangle
table ip filter
table ip6 mangle
table ip nat
table ip6 nat
table ip6 filter
table ip raw
table arp calico-arp
```

None of these tables is yours: the `ip` and `ip6` tables come from kube-proxy
(which writes through `iptables`, itself plugged into nftables), and
`calico-arp` comes from Calico. Count the rules they have set:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo iptables-save 2>/dev/null | grep -c -E "^-A (KUBE|cali)"; echo "(règles kube-proxy et Calico vues par iptables)"'
```

```text
202
(règles kube-proxy et Calico vues par iptables)
```

These rules make Services and the Pod network work. That is why your firewall
lives in **its own table** of the `inet` family, and why you never empty the
whole ruleset (`flush ruleset`) on a node.

## ✅ Exercise 2: check a rule before loading it

Write a test table that drops nothing (`policy accept`) but **counts** the
packets arriving on three ports: SSH (22), the kubelet (10250) and the
kube-proxy health port (10256). `nft -c` checks it without loading it:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'cat > /tmp/essai-comptage.nft <<"NFT"
table inet essai_comptage {
  chain entree {
    type filter hook input priority 10; policy accept;
    tcp dport 22 counter
    tcp dport 10250 counter
    tcp dport 10256 counter
  }
}
NFT
sudo nft -c -f /tmp/essai-comptage.nft; echo "vérification : code $?"'
```

```text
vérification : code 0
```

Code 0 says the file is valid. Now make a typo in the policy, and check again:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sed "s/policy accept;/policy acept;/" /tmp/essai-comptage.nft > /tmp/essai-faute.nft; sudo nft -c -f /tmp/essai-faute.nft 2>&1 | head -3'
```

```text
/tmp/essai-faute.nft:3:48-52: Error: syntax error, unexpected string, expecting accept or drop or '$'
    type filter hook input priority 10; policy acept;
                                               ^^^^^
```

`nft` gives the line, the column, and what it expected (`accept or drop`).
Nothing was loaded: that is the whole point of `-c` on a machine where a wrong
rule can cut off your access.

## 📊 Exercise 3: count what arrives

Load the test table, trigger a call from the API server to the kubelet of
`k8s-w1.lab` (a `kubectl logs` on a Pod running there), then read the
counters:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo nft -f /tmp/essai-comptage.nft'; P=$(kubectl -n kube-system get pods -l k8s-app=kube-proxy --field-selector spec.nodeName=k8s-w1.lab -o name); kubectl -n kube-system logs $P --tail=1 >/dev/null; echo "kubectl logs sur $P : code $?"; ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo nft list table inet essai_comptage | grep counter'
```

```text
kubectl logs sur pod/kube-proxy-pcbrz : code 0
		tcp dport 22 counter packets 21 bytes 4935
		tcp dport 10250 counter packets 7 bytes 3236
		tcp dport 10256 counter packets 0 bytes 0
```

Port 22 counts your own SSH session. Port 10250 counts the `kubectl logs`: the
API server does not read the logs itself, it asks the kubelet of the node on
this port. Port 10256 stays at 0: nobody queries the kube-proxy health in this
cluster. These counters, read over a real working day, tell you which ports a
`drop` policy must leave open, and from where.

## 🧽 Exercise 4: remove only your table

Delete the test table, and only it:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo nft delete table inet essai_comptage; sudo nft list tables; rm -f /tmp/essai-comptage.nft /tmp/essai-faute.nft'
```

```text
table ip mangle
table ip filter
table ip6 mangle
table ip nat
table ip6 nat
table ip6 filter
table ip raw
table arp calico-arp
```

The kube-proxy and Calico tables are all there, untouched: `nft delete table
inet essai_comptage` only touches yours. Check the node is fine:

```bash
kubectl get node k8s-w1.lab
```

```text
NAME         STATUS   ROLES    AGE   VERSION
k8s-w1.lab   Ready    <none>   22h   v1.37.2
```

## 🧹 Clean-up

Exercise 4 has already removed the test table and files: nothing is left on
`k8s-w1.lab`.

Leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cks-fermer-l-acces-reseau-au-noeud
dsoxlab check cks-fermer-l-acces-reseau-au-noeud
```

```text
╭─ Result: cks-fermer-l-acces-reseau-au-noeud ─╮
│  0 / 100 pts                                 │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests             │
╰──────────────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a worker with no firewall at all, to close
with a `drop` policy that lets the cluster flows through and survives a
reboot.

```bash
dsoxlab run cks-fermer-l-acces-reseau-au-noeud
dsoxlab challenge cks-fermer-l-acces-reseau-au-noeud
```
