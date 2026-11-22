# Trace who reads Secrets with the API server audit

The lesson shows how to write an audit policy and turn it on in the API
server. This course has you read a real audit log, for three points it does
not show: a request that produces two events, the order of the rules of the
policy, and an action made under another identity.

To leave alone the API server of the lab, whose configuration is the subject
of the challenge, you start a **test API server**: the same program, on port
6444, with its own policy and its own log in `/tmp/essai-audit`. It shares the
etcd of the cluster, under a separate prefix, `/essai-audit`, so it sees none
of the cluster objects. It allows everything (`AlwaysAllow`) and only listens
on `127.0.0.1`: it is an exercise tool, never a setting to copy.

Related page: [Audit Logs](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/audit-logs/) (in French).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-audit-log-policy
```

You are now logged into `k8s-cp.lab`, the node that drives the kubeadm cluster
(the control plane).

The outputs shown in this course were recorded on this machine on
22 November 2026, with Kubernetes v1.37.2.

Prepare the test API server: copy the program of the cluster API server,
write a policy that records everything at metadata level, and start it. The
command waits until it answers:

```bash
sudo mkdir -p /tmp/essai-audit; P=$(pgrep -xo kube-apiserver); sudo cp /proc/$P/root/usr/local/bin/kube-apiserver /tmp/essai-audit/; cat <<'YAML' | sudo tee /tmp/essai-audit/politique.yaml > /dev/null
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  - level: Metadata
YAML
sudo bash -c 'nohup /tmp/essai-audit/kube-apiserver --secure-port=6444 --bind-address=127.0.0.1 --cert-dir=/tmp/essai-audit/certs --etcd-servers=https://127.0.0.1:2379 --etcd-prefix=/essai-audit --etcd-cafile=/etc/kubernetes/pki/etcd/ca.crt --etcd-certfile=/etc/kubernetes/pki/apiserver-etcd-client.crt --etcd-keyfile=/etc/kubernetes/pki/apiserver-etcd-client.key --client-ca-file=/etc/kubernetes/pki/ca.crt --authorization-mode=AlwaysAllow --service-cluster-ip-range=10.96.0.0/12 --service-account-issuer=https://essai-audit --service-account-key-file=/etc/kubernetes/pki/sa.pub --service-account-signing-key-file=/etc/kubernetes/pki/sa.key --audit-policy-file=/tmp/essai-audit/politique.yaml --audit-log-path=/tmp/essai-audit/audit.log > /tmp/essai-audit/serveur.log 2>&1 & echo $! > /tmp/essai-audit/pid'; until sudo test -f /tmp/essai-audit/certs/apiserver.crt && sudo chmod 0644 /tmp/essai-audit/certs/apiserver.crt && kubectl --server=https://127.0.0.1:6444 --certificate-authority=/tmp/essai-audit/certs/apiserver.crt get --raw /livez > /dev/null 2>&1; do sleep 2; done; echo 'API server de test prêt'
```

```text
API server de test prêt
```

All the `kubectl` commands of this course target that server with
`--server=https://127.0.0.1:6444`. It keeps its PID in `/tmp/essai-audit/pid`,
used to stop it. An audit policy is only read at startup: every policy change
means restarting it.

## 📨 Exercise 1: one request, two events

List the namespaces of the test server, then read what the log kept of that
request:

```bash
kubectl --server=https://127.0.0.1:6444 --certificate-authority=/tmp/essai-audit/certs/apiserver.crt get namespaces > /dev/null; sudo jq -c 'select(.verb=="list" and .objectRef.resource=="namespaces") | {stage, level, utilisateur: .user.username, verb, ressource: .objectRef.resource}' /tmp/essai-audit/audit.log | tail -2
```

```text
{"stage":"RequestReceived","level":"Metadata","utilisateur":"kubernetes-admin","verb":"list","ressource":"namespaces"}
{"stage":"ResponseComplete","level":"Metadata","utilisateur":"kubernetes-admin","verb":"list","ressource":"namespaces"}
```

One request, two events. The first one is written on receipt
(`RequestReceived`), the second once the response has gone out
(`ResponseComplete`). On a real cluster, that duplicate weighs on the log
volume: that is what `omitStages` removes.

## 🔀 Exercise 2: the first matching rule wins

Write a policy that wants to record ConfigMaps in full (`RequestResponse`),
but puts a general Metadata rule first. Restart the server, create a
ConfigMap, and read its level:

```bash
cat <<'YAML' | sudo tee /tmp/essai-audit/politique.yaml > /dev/null
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  - level: Metadata
  - level: RequestResponse
    resources:
      - group: ""
        resources: [configmaps]
YAML
sudo kill $(sudo cat /tmp/essai-audit/pid); sleep 3; sudo bash -c 'nohup /tmp/essai-audit/kube-apiserver --secure-port=6444 --bind-address=127.0.0.1 --cert-dir=/tmp/essai-audit/certs --etcd-servers=https://127.0.0.1:2379 --etcd-prefix=/essai-audit --etcd-cafile=/etc/kubernetes/pki/etcd/ca.crt --etcd-certfile=/etc/kubernetes/pki/apiserver-etcd-client.crt --etcd-keyfile=/etc/kubernetes/pki/apiserver-etcd-client.key --client-ca-file=/etc/kubernetes/pki/ca.crt --authorization-mode=AlwaysAllow --service-cluster-ip-range=10.96.0.0/12 --service-account-issuer=https://essai-audit --service-account-key-file=/etc/kubernetes/pki/sa.pub --service-account-signing-key-file=/etc/kubernetes/pki/sa.key --audit-policy-file=/tmp/essai-audit/politique.yaml --audit-log-path=/tmp/essai-audit/audit.log > /tmp/essai-audit/serveur.log 2>&1 & echo $! > /tmp/essai-audit/pid'; until sudo test -f /tmp/essai-audit/certs/apiserver.crt && sudo chmod 0644 /tmp/essai-audit/certs/apiserver.crt && kubectl --server=https://127.0.0.1:6444 --certificate-authority=/tmp/essai-audit/certs/apiserver.crt get --raw /livez > /dev/null 2>&1; do sleep 2; done; echo 'API server de test prêt'; kubectl --server=https://127.0.0.1:6444 --certificate-authority=/tmp/essai-audit/certs/apiserver.crt create configmap essai-ordre --from-literal=cle=valeur > /dev/null; sudo jq -c 'select(.verb=="create" and .objectRef.name=="essai-ordre") | {stage, level}' /tmp/essai-audit/audit.log
```

```text
API server de test prêt
{"stage":"ResponseComplete","level":"Metadata"}
```

`Metadata`: the first rule matches every request, so the second one is never
read. The API server walks the rules in order, and stops at the first one that
matches. Swap the order, and drop the `RequestReceived` stage:

```bash
cat <<'YAML' | sudo tee /tmp/essai-audit/politique.yaml > /dev/null
apiVersion: audit.k8s.io/v1
kind: Policy
omitStages: [RequestReceived]
rules:
  - level: RequestResponse
    resources:
      - group: ""
        resources: [configmaps]
  - level: Metadata
YAML
sudo kill $(sudo cat /tmp/essai-audit/pid); sleep 3; sudo bash -c 'nohup /tmp/essai-audit/kube-apiserver --secure-port=6444 --bind-address=127.0.0.1 --cert-dir=/tmp/essai-audit/certs --etcd-servers=https://127.0.0.1:2379 --etcd-prefix=/essai-audit --etcd-cafile=/etc/kubernetes/pki/etcd/ca.crt --etcd-certfile=/etc/kubernetes/pki/apiserver-etcd-client.crt --etcd-keyfile=/etc/kubernetes/pki/apiserver-etcd-client.key --client-ca-file=/etc/kubernetes/pki/ca.crt --authorization-mode=AlwaysAllow --service-cluster-ip-range=10.96.0.0/12 --service-account-issuer=https://essai-audit --service-account-key-file=/etc/kubernetes/pki/sa.pub --service-account-signing-key-file=/etc/kubernetes/pki/sa.key --audit-policy-file=/tmp/essai-audit/politique.yaml --audit-log-path=/tmp/essai-audit/audit.log > /tmp/essai-audit/serveur.log 2>&1 & echo $! > /tmp/essai-audit/pid'; until sudo test -f /tmp/essai-audit/certs/apiserver.crt && sudo chmod 0644 /tmp/essai-audit/certs/apiserver.crt && kubectl --server=https://127.0.0.1:6444 --certificate-authority=/tmp/essai-audit/certs/apiserver.crt get --raw /livez > /dev/null 2>&1; do sleep 2; done; echo 'API server de test prêt'; kubectl --server=https://127.0.0.1:6444 --certificate-authority=/tmp/essai-audit/certs/apiserver.crt create configmap essai-ordre-2 --from-literal=cle=valeur > /dev/null; sudo jq -c 'select(.verb=="create" and .objectRef.name=="essai-ordre-2") | {stage, level, corps: .requestObject.data}' /tmp/essai-audit/audit.log
```

```text
API server de test prêt
{"stage":"ResponseComplete","level":"RequestResponse","corps":{"cle":"valeur"}}
```

This time, `RequestResponse`, a single event, and the body of the request
(`cle: valeur`) is in the log. Specific rule first, general rule last: it is
the most frequent mistake in an audit policy, and it produces no error
message.

## 🎭 Exercise 3: an action made under another identity

`kubectl --as` lets you act on behalf of another user, if you are allowed to.
Delete the first ConfigMap on behalf of `alice`, then look for who deleted it:

```bash
kubectl --server=https://127.0.0.1:6444 --certificate-authority=/tmp/essai-audit/certs/apiserver.crt delete configmap essai-ordre --as=alice > /dev/null; sudo jq -c 'select(.verb=="delete" and .objectRef.name=="essai-ordre") | {qui: .user.username, pour: .impersonatedUser.username, verb, objet: .objectRef.name, quand: .requestReceivedTimestamp}' /tmp/essai-audit/audit.log
```

```text
{"qui":"kubernetes-admin","pour":"alice","verb":"delete","objet":"essai-ordre","quand":"2026-11-22T10:57:53.827115Z"}
```

The log keeps both identities: `kubernetes-admin` made the request, on behalf
of `alice` (`impersonatedUser`), with the exact time. An investigation that
only looked at `impersonatedUser` would wrongly blame `alice`: `user` is what
says who really acted.

## 🧹 Clean-up

Stop the test server, delete its data from the `/essai-audit` prefix of etcd,
then its folder:

```bash
sudo kill $(sudo cat /tmp/essai-audit/pid); sleep 3; sudo kubectl --kubeconfig /etc/kubernetes/admin.conf -n kube-system exec etcd-k8s-cp.lab -- etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key del --prefix /essai-audit; sudo rm -rf /tmp/essai-audit; ls -d /tmp/essai-audit
```

```text
56
ls: cannot access '/tmp/essai-audit': No such file or directory
```

`etcdctl` deleted the keys of the test prefix (the number shown), and the
folder no longer exists. The cluster API server was never changed.

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cks-audit-log-policy
dsoxlab check cks-audit-log-policy
```

```text
╭── Result: cks-audit-log-policy ───╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/7 tests  │
╰───────────────────────────────────╯
```

0 out of 7: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: give the cluster API server a policy that
records Secret accesses in full and everything else as metadata, without it
ceasing to answer.

```bash
dsoxlab run cks-audit-log-policy
dsoxlab challenge cks-audit-log-policy
```
