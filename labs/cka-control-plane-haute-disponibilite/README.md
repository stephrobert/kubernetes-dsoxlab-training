# Build a kubeadm control plane with three nodes behind a load balancer, and lose one

The lesson shows how to build a three-node control plane behind a load
balancer, so that the cluster survives losing a machine. The lab prepared the
machines without a cluster: building it is the challenge. This course
therefore creates no cluster. It adds cases the lesson does not show: a load
balancer that accepts connections while no API answers, the endpoint baked
into the API server's certificate, the certificate key, and how many etcd
members you can lose.

You work in a scratch directory, `~/essai-ha`. The challenge is about the
real cluster behind `ha-lb.lab:6443`: you will do it on your own, at the end.

Related page: [Highly available control plane](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/ha-control-plane/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-control-plane-haute-disponibilite
```

The lab builds four machines: three future control planes and an HAProxy load
balancer. You are now connected to `ha-cp1.lab`. There is no cluster yet.

The outputs shown in this course were recorded on this machine on 21 November
2026, with kubeadm v1.37.

## ⚖️ Exercise 1: a load balancer that answers with no API behind it

Look at how the four machines' names resolve:

```bash
getent hosts ha-lb.lab ha-cp1.lab ha-cp2.lab ha-cp3.lab
```

```text
10.10.50.21     ha-lb.lab ha-lb
127.0.1.1       ha-cp1.lab.lab ha-cp1.lab ha-cp1 ha-cp1.lab
10.10.50.18     ha-cp1.lab.lab ha-cp1.lab ha-cp1 ha-cp1.lab
10.10.50.19     ha-cp2.lab ha-cp2
10.10.50.20     ha-cp3.lab ha-cp3
```

The `ha-lb.lab` load balancer has its own address, separate from the three
nodes. Test it two ways: a plain TCP connection on port 6443, then a real
HTTPS request to the API (`connexion TCP au répartiteur` means "TCP
connection to the load balancer", `requête HTTPS` "HTTPS request"):

```bash
nc -z -w 3 ha-lb.lab 6443; echo "connexion TCP au répartiteur : code $?"; curl -sk -m 5 "https://ha-lb.lab:6443/healthz"; echo "requête HTTPS : code $?"
```

```text
Connection to ha-lb.lab (10.10.50.21) 6443 port [tcp/*] succeeded!
connexion TCP au répartiteur : code 0
requête HTTPS : code 35
```

The TCP connection succeeds, but the HTTPS request fails (curl code 35: the
TLS exchange did not complete). HAProxy accepts the connection, then finds no
running API server behind it, and cuts it. An open port therefore does not
prove an API answers: always check with a request that goes all the way to
the API, such as `/healthz`.

## 🔏 Exercise 2: the endpoint is baked into the certificate

`kubeadm init` is split into phases, which can be run one by one. In a
scratch directory, have kubeadm generate a certificate authority then the API
server's certificate, with the load balancer as the endpoint:

```bash
mkdir -p ~/essai-ha; kubeadm init phase certs ca --cert-dir ~/essai-ha/pki >/dev/null; kubeadm init phase certs apiserver --cert-dir ~/essai-ha/pki --control-plane-endpoint ha-lb.lab:6443 --apiserver-advertise-address $(hostname -I | cut -d' ' -f1); ls ~/essai-ha/pki
```

```text
[certs] Generating "apiserver" certificate and key
[certs] apiserver serving cert is signed for DNS names [ha-cp1.lab ha-lb.lab kubernetes kubernetes.default kubernetes.default.svc kubernetes.default.svc.cluster.local] and IPs [10.96.0.1 10.10.50.18]
apiserver.crt
apiserver.key
ca.crt
ca.key
```

Read the names this certificate covers:

```bash
openssl x509 -in ~/essai-ha/pki/apiserver.crt -noout -ext subjectAltName
```

```text
X509v3 Subject Alternative Name: 
    DNS:ha-cp1.lab, DNS:ha-lb.lab, DNS:kubernetes, DNS:kubernetes.default, DNS:kubernetes.default.svc, DNS:kubernetes.default.svc.cluster.local, IP Address:10.96.0.1, IP Address:10.10.50.18
```

`ha-lb.lab` is among the certificate's names, with the node's name and
Kubernetes' internal names. That is why the endpoint can no longer be changed
after initialisation: clients check this certificate, and a new name would not
be in it. Nothing was installed: everything is in `~/essai-ha`.

## 🔑 Exercise 3: the certificate key

With `--upload-certs`, `kubeadm init` stores the cluster's certificates in a
Secret, encrypted with a certificate key. The other control planes need it to
join. Have one generated:

```bash
kubeadm certs certificate-key; kubeadm certs certificate-key | wc -c
```

```text
6bed1af7ece6bf6f7b7fde11cad0400686e6ab46183d63688b68c495a38d19e0
65
```

64 hexadecimal characters (plus the newline counted by `wc`), that is a
32-byte key. A new key is drawn at each call. This key gives access to the
cluster's certificates: it is handed over like a password, and the Secret it
protects is deleted after two hours.

## 🗳️ Exercise 4: how many etcd members can you lose?

etcd only accepts a write if a majority of its members, the quorum, agrees.
Compute, for 1 to 5 members, the quorum and the number of failures tolerated
(`membres` means "members", `panne tolérée` "failure tolerated"):

```bash
for n in 1 2 3 4 5; do q=$(( n / 2 + 1 )); echo "$n membres : quorum $q, panne tolérée $(( n - q ))"; done
```

```text
1 membres : quorum 1, panne tolérée 0
2 membres : quorum 2, panne tolérée 0
3 membres : quorum 2, panne tolérée 1
4 membres : quorum 3, panne tolérée 1
5 membres : quorum 3, panne tolérée 2
```

Three members tolerate one failure, four members too. An even number brings
nothing: it adds a machine that can fail without adding tolerance. That is why
the challenge, like most clusters, uses three control planes.

## 🧹 Clean-up

Delete the scratch directory:

```bash
rm -rf ~/essai-ha; ls ~/essai-ha 2>&1
```

```text
ls: cannot access '/home/ansible/essai-ha': No such file or directory
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-control-plane-haute-disponibilite
dsoxlab check cka-control-plane-haute-disponibilite
```

```text
╭─ Result: cka-control-plane-haute-disponibilite ─╮
│  0 / 100 pts                                    │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests                │
╰─────────────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: build the three-node control plane behind
the load balancer, then prove it survives losing a node.

```bash
dsoxlab run cka-control-plane-haute-disponibilite
dsoxlab challenge cka-control-plane-haute-disponibilite
```
