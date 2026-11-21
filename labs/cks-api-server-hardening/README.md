# Close the API server profiler, without closing the API

The lesson presents the CIS Benchmark and the settings that harden a cluster.
Here, changing the API server is the challenge: this course does not touch its
manifest. It measures from the outside what the API server and the kubelet
allow, with cases the lesson does not show: what an anonymous client gets
from each, the kubelet's authentication settings, and the TLS versions both
really accept.

Related page: [CIS Kubernetes Benchmark: audit your cluster security](https://www.stephane-robert.info/en/docs/devsecops/runtime/cis-benchmark/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-api-server-hardening
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2 and OpenSSL 3.0.13.

## 👤 Exercise 1: what an anonymous client gets from the API server

`curl` without a certificate or a token presents itself as anonymous. Query
three paths of the API server, and read the response code:

```bash
for p in /version /healthz /api/v1/namespaces; do printf '%-22s -> ' $p; curl -sk -o /dev/null -w '%{http_code}\n' "https://127.0.0.1:6443$p"; done
```

```text
/version               -> 200
/healthz               -> 200
/api/v1/namespaces     -> 403
```

`/version` and `/healthz` answer, the list of namespaces is refused (403). The
anonymous client is recognised, but has almost no rights. What it has left
comes from this binding:

```bash
kubectl get clusterrolebinding system:public-info-viewer -o jsonpath='{.subjects[*].name}{"\n"}'
```

```text
system:authenticated system:unauthenticated
```

The `system:public-info-viewer` role is granted to everyone, logged in or
not: it is what opens `/version` and `/healthz`.

## 🔒 Exercise 2: what an anonymous client gets from the kubelet

Each node's kubelet exposes its own API on port 10250. Try the same on the one
of `k8s-w1.lab`:

```bash
W1=$(kubectl get node k8s-w1.lab -o jsonpath='{.status.addresses[0].address}'); for p in /healthz /pods; do printf 'kubelet %-9s -> ' $p; curl -sk -o /dev/null -w '%{http_code}\n' "https://$W1:10250$p"; done
```

```text
kubelet /healthz  -> 401
kubelet /pods     -> 401
```

401 everywhere: the kubelet does not even recognise the anonymous client. Its
configuration says so:

```bash
sudo grep -A6 -E '^authentication:|^authorization:' /var/lib/kubelet/config.yaml | head -14
```

```text
authentication:
  anonymous:
    enabled: false
  webhook:
    cacheTTL: 0s
    enabled: true
  x509:
--
authorization:
  mode: Webhook
  webhook:
    cacheAuthorizedTTL: 0s
    cacheUnauthorizedTTL: 0s
cgroupDriver: systemd
```

`anonymous.enabled: false` refuses clients without an identity. `mode:
Webhook` has each request checked by the API server, with the same RBAC rules
as the rest of the cluster.

## 🔐 Exercise 3: the TLS versions the servers accept

First test TLS 1.1 on the API server with `openssl`:

```bash
echo | openssl s_client -connect 127.0.0.1:6443 -tls1_1 2>&1 | grep -o -m1 'no protocols available'
```

```text
no protocols available
```

Careful, this refusal comes from the **client**: OpenSSL 3 disables TLS 1.1 on
its side, without even contacting the server. To measure the server, TLS 1.1
must be enabled again on the client side with `SECLEVEL=0`:

```bash
W1=$(kubectl get node k8s-w1.lab -o jsonpath='{.status.addresses[0].address}'); for cible in $W1:10250 127.0.0.1:6443; do for v in tls1_1 tls1_2 tls1_3; do printf '%-18s %s -> ' $cible $v; echo | openssl s_client -connect $cible -$v -cipher 'DEFAULT@SECLEVEL=0' 2>&1 | grep -o -m1 -E 'New, TLSv1\.[0-9]|alert protocol version'; done; done
```

```text
10.10.50.12:10250  tls1_1 -> alert protocol version
10.10.50.12:10250  tls1_2 -> New, TLSv1.2
10.10.50.12:10250  tls1_3 -> New, TLSv1.3
127.0.0.1:6443     tls1_1 -> alert protocol version
127.0.0.1:6443     tls1_2 -> New, TLSv1.2
127.0.0.1:6443     tls1_3 -> New, TLSv1.3
```

This time it is indeed the server that refuses TLS 1.1 (`alert protocol
version`), on the kubelet as on the API server. Both accept TLS 1.2 and 1.3. A
TLS version test is only worth something if the client can offer the version
being tested.

## 🧹 Clean-up

The course created no object. Leave the machine and reset the lab.
`dsoxlab reset` replays the lab's clean-up then its preparation: you get back
exactly the starting state of the challenge. It asks you to confirm: answer
`y`.

```bash
exit
dsoxlab reset cks-api-server-hardening
dsoxlab check cks-api-server-hardening
```

```text
╭─ Result: cks-api-server-hardening ─╮
│  0 / 100 pts                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/2 tests   │
╰────────────────────────────────────╯
```

0 out of 2: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: close the API server's profiler and drop its
weakest cipher suites, without breaking the API.

```bash
dsoxlab run cks-api-server-hardening
dsoxlab challenge cks-api-server-hardening
```
