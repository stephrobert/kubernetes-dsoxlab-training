# Enforce mTLS between the Pods of an Istio mesh

The lesson shows how mTLS between Pods works, and how Istio enforces it with a
PeerAuthentication in STRICT mode. This course adds what to check before
requiring anything: that a Pod really carries its sidecar, the identity
written in its certificate, and the mTLS mode Istio actually applies to it.

You work in the `essai-mtls` namespace, with a `serveur` Pod. The challenge
targets other namespaces and other Pods: you will do it on your own, at the
end.

Related page: [mTLS between Pods](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/mtls-pod-to-pod/) (in French).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-istio-mtls-lockdown
```

You are now logged into `k8s-cp.lab`, the node that drives the kubeadm cluster
(the control plane). Istio is installed in the cluster, and `istioctl` on the
node.

The outputs shown in this course were recorded on this machine on
22 November 2026, with Istio 1.31.0.

## 💉 Exercise 1: injection is decided when the Pod is created

Istio adds its sidecar to the Pods of a namespace that carries the
`istio-injection=enabled` label. Create a namespace without that label, start
an HTTP server in it, then set the label:

```bash
kubectl create namespace essai-mtls; kubectl run serveur -n essai-mtls --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --port=8080 -- httpd -f -p 8080; kubectl wait --for=condition=Ready pod/serveur -n essai-mtls --timeout=120s; kubectl label namespace essai-mtls istio-injection=enabled; kubectl get pod serveur -n essai-mtls
```

```text
namespace/essai-mtls created
pod/serveur created
pod/serveur condition met
namespace/essai-mtls labeled
NAME      READY   STATUS    RESTARTS   AGE
serveur   1/1     Running   0          1s
```

The Pod stays at `1/1`: one container, no sidecar. Injection is done by an
admission webhook, when the Pod is **created**. A label set afterwards does
not touch the Pods already running. Recreate the Pod:

```bash
kubectl delete pod serveur -n essai-mtls --wait=true; kubectl run serveur -n essai-mtls --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --port=8080 -- httpd -f -p 8080; kubectl wait --for=condition=Ready pod/serveur -n essai-mtls --timeout=180s; kubectl get pod serveur -n essai-mtls; kubectl get pod serveur -n essai-mtls -o jsonpath='{range .spec.initContainers[*]}{.name}{" restartPolicy="}{.restartPolicy}{"\n"}{end}'
```

```text
pod "serveur" deleted from essai-mtls namespace
pod/serveur created
pod/serveur condition met
NAME      READY   STATUS    RESTARTS   AGE
serveur   2/2     Running   0          2s
istio-init restartPolicy=
istio-proxy restartPolicy=Always
```

`2/2` this time. The `istio-proxy` sidecar is an init container with
`restartPolicy: Always`, the form of native Kubernetes sidecars: it starts
before the application and lives as long as it does. `istio-init` sets up the
traffic redirection, then stops. In a namespace you open to the mesh, the
existing Pods must therefore be restarted, or they stay out of the mesh
without anything saying so.

## 🪪 Exercise 2: the identity of the Pod, and the mTLS mode applied

The sidecar gets a certificate from Istio, which proves the identity of the
Pod to the others. Read it in the proxy configuration:

```bash
istioctl proxy-config secret serveur -n essai-mtls -o json | jq -r '.dynamicActiveSecrets[] | select(.name=="default") | .secret.tlsCertificate.certificateChain.inlineBytes' | base64 -d | openssl x509 -noout -subject -ext subjectAltName -enddate
```

```text
subject=
X509v3 Subject Alternative Name: critical
    URI:spiffe://cluster.local/ns/essai-mtls/sa/default
notAfter=Nov 23 10:43:24 2026 GMT
```

The identity is a SPIFFE URI: `spiffe://cluster.local/ns/essai-mtls/sa/default`.
It comes from the namespace and the service account of the Pod, not from its
name or its IP address. The certificate expires the next day: Istio renews it
itself, well before. That identity is what an AuthorizationPolicy names to
allow or refuse a caller.

Finally, ask `istioctl` for the mTLS mode Istio applies to this Pod:

```bash
istioctl x describe pod serveur -n essai-mtls 2>&1 | grep -iE 'pod:|mtls|peerauthentication|strict|permissive' | head -6
```

```text
Pod: serveur
Effective PeerAuthentication:
   Workload mTLS mode: PERMISSIVE
```

`PERMISSIVE`: the Pod accepts encrypted **and** plain traffic. That is the
default mode of Istio, which lets you migrate without cutting anything off. As
long as no PeerAuthentication says otherwise, a client outside the mesh
reaches this Pod in plain text.

## 🧹 Clean-up

Delete the test namespace:

```bash
kubectl delete namespace essai-mtls --wait=true --timeout=120s
```

```text
namespace "essai-mtls" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cks-istio-mtls-lockdown
dsoxlab check cks-istio-mtls-lockdown
```

```text
╭─ Result: cks-istio-mtls-lockdown ─╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/2 tests  │
╰───────────────────────────────────╯
```

That is the expected result on a fresh lab. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a mesh where encryption is possible but not
required, to close to clients without a certificate without cutting the
application off.

```bash
dsoxlab run cks-istio-mtls-lockdown
dsoxlab challenge cks-istio-mtls-lockdown
```
