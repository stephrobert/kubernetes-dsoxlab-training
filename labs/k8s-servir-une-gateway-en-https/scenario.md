# Serve an Istio Gateway over HTTPS with a cert-manager certificate

## The situation

The kubeadm cluster now has **three nodes**: the control plane and two
workers. Istio 1.32 runs on it in **ambient mode**, and the Gateway API
v1.6.1 is installed: the GatewayClass **`istio`** is ready to deploy an Envoy
for every Gateway you declare.

cert-manager v1.21.3 is installed too, with an internal certificate
authority: the ClusterIssuer **`ca-formation`** signs certificates for the
whole cluster. Its own certificate is in the Secret `ca-formation` of the
`cert-manager` namespace.

In the namespace **`vitrine`**, the application `vitrine` answers in plain
HTTP behind the Service `vitrine` (port 80). The team wants it served over
HTTPS under the name **`vitrine.formation.test`**, through a Gateway, with a
certificate that cert-manager issues and renews.

The cluster has **no load balancer**. You are on the control plane, with
`kubectl` configured, as root.

## What you must achieve

1. A cert-manager **Certificate** for `vitrine.formation.test`, issued by the
   ClusterIssuer `ca-formation`, is **Ready** in the namespace `vitrine`.
2. A **Gateway** of class `istio` in `vitrine` has an **HTTPS listener on port
   443** that terminates TLS with the Secret of that certificate, and the
   cluster declares it **Programmed**.
3. The listener **presents** the certificate that cert-manager stored, for
   the name `vitrine.formation.test`.
4. The presented certificate is **issued by the internal CA**, and its chain
   verifies against it.
5. An HTTPS client that trusts **only** the internal CA reaches the
   application `vitrine` through the Gateway.

## The method, step by step

**Request the certificate where the Gateway lives.** A listener reads its
certificate from a Secret of **its own namespace**. Another namespace is
possible only with a `ReferenceGrant`, which this lab does not need. So the
`Certificate` goes into `vitrine`: `dnsNames` carries the name, `issuerRef`
points at the **ClusterIssuer** `ca-formation` (the kind matters: no `Issuer`
of that name exists), and `secretName` names the Secret cert-manager will
write. `kubectl get certificate -n vitrine` must show `READY True`.

**Declare the Gateway.** `gatewayClassName: istio`, one listener with
`protocol: HTTPS`, `port: 443`, `hostname: vitrine.formation.test`, and a
`tls` block in `mode: Terminate` whose `certificateRefs` names the Secret.
Istio creates a Deployment and a Service for it in the same namespace.

**Mind the address.** By default Istio asks for a Service of type
`LoadBalancer`. On a cluster without a load balancer, that Service never gets
an address, and the Gateway stays **not Programmed**: `kubectl describe
gateway` says why. The annotation `networking.istio.io/service-type:
ClusterIP` on the Gateway asks for an internal address instead.

**Attach a route.** An `HTTPRoute` in `vitrine`, with `parentRefs` to the
Gateway (and `sectionName` to the listener if you want to be explicit),
`hostnames` with the name, and a `backendRef` to the Service `vitrine`, port
80. Without it, the Gateway answers 404.

**Check like a client.** Take the ClusterIP of the Service Istio created
(`kubectl get svc -n vitrine -l gateway.networking.k8s.io/gateway-name=<name>`).
`openssl s_client -connect <ip>:443 -servername vitrine.formation.test` shows
the certificate presented and its issuer. Extract the CA with `kubectl get
secret ca-formation -n cert-manager -o jsonpath='{.data.tls\.crt}' | base64
-d > ca.crt`, then `curl --cacert ca.crt --resolve
vitrine.formation.test:443:<ip> https://vitrine.formation.test/` must answer
`vitrine`, without `-k`.

## How you will know it works

The tests look for your Certificate and its readiness, read the conditions of
the Gateway and of its listener, then open a real TLS connection to the
listener: they compare the certificate presented with the Secret cert-manager
wrote, verify it against the internal CA, and send an HTTPS request that must
reach the application.

```bash
dsoxlab check k8s-servir-une-gateway-en-https
```
