# Filter at L7 with Cilium

The lesson serves an application through a Cilium Gateway, then applies a
policy that filters HTTP requests by their method. This course touches
neither the Gateway nor the method: that is the challenge of this lab. It
practises Cilium HTTP policies on other criteria, the path and a header, and
teaches you to recognise their refusals: the answer the client gets, the line
Hubble shows, and the difference with a refusal at the port level.

You work in the `essai-l7` namespace, with an nginx server `doc` and a
client `visiteur`. The challenge uses other Pods, in `catalogue`: you will do
it on your own, at the end.

Related page: [Serve a Gateway and filter at L7 with Cilium](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/cilium-gateway-l7/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-filtrer-en-l7-avec-cilium
```

You are now connected to `net-cp.lab`, the control plane of the Cilium
cluster. Create the scratch objects: the `doc` server on `net-w1`, its
Service, and the `visiteur` client on `net-w2`:

```bash
kubectl create namespace essai-l7; cat <<'YAML' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: doc
  namespace: essai-l7
  labels:
    app: doc
spec:
  nodeName: net-w1.lab
  containers:
    - name: web
      image: nginx:1.30.6
---
apiVersion: v1
kind: Service
metadata:
  name: doc
  namespace: essai-l7
spec:
  selector:
    app: doc
  ports:
    - port: 80
---
apiVersion: v1
kind: Pod
metadata:
  name: visiteur
  namespace: essai-l7
  labels:
    app: visiteur
spec:
  nodeName: net-w2.lab
  containers:
    - name: c
      image: curlimages/curl:8.22.0
      command: ["sleep", "3600"]
YAML
kubectl -n essai-l7 wait --for=condition=Ready pod --all --timeout=120s
```

```text
namespace/essai-l7 created
pod/doc created
service/doc created
pod/visiteur created
pod/doc condition met
pod/visiteur condition met
```

The outputs shown in this course were captured on these machines on
22 November 2026 (Kubernetes v1.37.2, Cilium 1.20.5).

## 🚪 Exercise 1: a Gateway without its definitions

A Gateway is a Gateway API resource, which Kubernetes does not know until its
CRDs (the definitions of new object types) are installed. The lab cluster
does not have them. Have the API server validate a scratch Gateway, without
creating anything (`--dry-run=server`), then list the types the
`gateway.networking.k8s.io` group knows:

```bash
cat > /tmp/essai-gateway.yaml <<'YAML'
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: essai
  namespace: essai-l7
spec:
  gatewayClassName: cilium
  listeners:
    - name: web
      protocol: HTTP
      port: 80
YAML
kubectl apply --dry-run=server -f /tmp/essai-gateway.yaml; echo "code=$?"
kubectl api-resources --api-group=gateway.networking.k8s.io
rm /tmp/essai-gateway.yaml
```

```text
error: resource mapping not found for name: "essai" namespace: "essai-l7" from "/tmp/essai-gateway.yaml": no matches for kind "Gateway" in version "gateway.networking.k8s.io/v1"
ensure CRDs are installed first
code=1
NAME   SHORTNAMES   APIVERSION   NAMESPACED   KIND
```

`no matches for kind "Gateway"`: the API server does not know this type, and
`kubectl` says so itself, `ensure CRDs are installed first`. The list of the
group's types is empty. This message mentions neither Cilium nor the `cilium`
class: as long as it shows up, the problem sits before Cilium.

## 🛣️ Exercise 2: filter by path

Without a policy, the client reads every page of the server. nginx serves
`/index.html` and an error page, `/50x.html`:

```bash
for p in /index.html /50x.html; do echo "$p -> $(kubectl -n essai-l7 exec visiteur -- curl -s -o /dev/null -w '%{http_code}' "http://doc$p")"; done
```

```text
/index.html -> 200
/50x.html -> 200
```

Apply a CiliumNetworkPolicy that only allows the `/index.html` path to the
client. The `rules.http` section sends port 80 traffic through the Cilium
proxy, which reads each request:

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: doc-chemins
  namespace: essai-l7
spec:
  endpointSelector:
    matchLabels:
      app: doc
  ingress:
    - fromEndpoints:
        - matchLabels:
            app: visiteur
      toPorts:
        - ports:
            - port: "80"
              protocol: TCP
          rules:
            http:
              - path: "/index.html"
YAML
sleep 10
for p in /index.html /50x.html; do echo "$p -> $(kubectl -n essai-l7 exec visiteur -- curl -s -o /dev/null -w '%{http_code}' "http://doc$p")"; done
kubectl -n essai-l7 exec visiteur -- curl -s http://doc/50x.html
```

```text
ciliumnetworkpolicy.cilium.io/doc-chemins created
/index.html -> 200
/50x.html -> 403
Access denied
```

`/50x.html` is now refused with **403**, and the body `Access denied`. It is
not nginx answering: it is the Cilium proxy, which read the path and refused
the request before it reached the server. An L7 refusal is therefore seen
right away, with an HTTP answer.

## 🔭 Exercise 3: the refusal seen by Hubble

The refusal also shows in Hubble, on the agent of the server's node, which
holds the ingress policy. The `--protocol http` filter only keeps the flows
the proxy read:

```bash
w1=$(kubectl -n kube-system get pods -l k8s-app=cilium --field-selector spec.nodeName=net-w1.lab -o name)
kubectl -n kube-system exec $w1 -c cilium-agent -- hubble observe --namespace essai-l7 --protocol http --last 4
```

```text
Nov 22 22:47:34.827: essai-l7/visiteur:35854 (ID:7450) -> essai-l7/doc:80 (ID:31715) http-request DROPPED (HTTP/1.1 GET http://doc/50x.html)
Nov 22 22:47:34.827: essai-l7/visiteur:35854 (ID:7450) <- essai-l7/doc:80 (ID:31715) http-response FORWARDED (HTTP/1.1 403 0ms (GET http://doc/50x.html))
Nov 22 22:47:34.894: essai-l7/visiteur:35862 (ID:7450) -> essai-l7/doc:80 (ID:31715) http-request DROPPED (HTTP/1.1 GET http://doc/50x.html)
Nov 22 22:47:34.894: essai-l7/visiteur:35862 (ID:7450) <- essai-l7/doc:80 (ID:31715) http-response FORWARDED (HTTP/1.1 403 0ms (GET http://doc/50x.html))
```

Each refused request gives two lines. The request, with its method and full
URL, is `DROPPED`. The answer, a `403` produced in less than a millisecond
(`0ms`), is `FORWARDED`: the proxy sends it back to the client. Hubble names
the exact request, which a port refusal cannot do.

## 🏷️ Exercise 4: require a header

An HTTP rule can also require a header. Change the policy so that it asks for
`X-Essai: oui` on top of the path, then test with and without the header:

```bash
kubectl -n essai-l7 patch cnp doc-chemins --type=json -p='[{"op":"replace","path":"/spec/ingress/0/toPorts/0/rules/http/0","value":{"path":"/index.html","headers":["X-Essai: oui"]}}]'
sleep 10
echo "sans en-tete -> $(kubectl -n essai-l7 exec visiteur -- curl -s -o /dev/null -w '%{http_code}' 'http://doc/index.html')"
echo "avec en-tete -> $(kubectl -n essai-l7 exec visiteur -- curl -s -o /dev/null -w '%{http_code}' -H 'X-Essai: oui' 'http://doc/index.html')"
```

```text
ciliumnetworkpolicy.cilium.io/doc-chemins patched
sans en-tete -> 403
avec en-tete -> 200
```

The fields of one rule combine: the path **and** the header must match
(`sans en-tete` means without the header, `avec` with it). Without the
header, the page allowed in exercise 2 becomes refused. An HTTP rule does not
replace authentication: any client that knows the header can send it.

## 🔌 Exercise 5: a refusal at the port level

Now change the port of the rule, 8080 instead of 80, like a typo. Port 80 is
no longer allowed at all:

```bash
kubectl -n essai-l7 patch cnp doc-chemins --type=json -p='[{"op":"replace","path":"/spec/ingress/0/toPorts/0/ports/0/port","value":"8080"}]'
sleep 10
time kubectl -n essai-l7 exec visiteur -- curl -s -m 5 -o /dev/null -w '%{http_code}\n' http://doc/index.html
echo "code=$?"
```

```text
ciliumnetworkpolicy.cilium.io/doc-chemins patched
000
command terminated with exit code 28

real	0m5.076s
user	0m0.033s
sys	0m0.013s
code=28
```

No more 403: `curl` waits for the 5 seconds of `-m 5`, then gives up (code 28,
timeout), without any HTTP code (`000`). The packet is dropped before the
proxy, and nobody answers. Remember the difference: **an immediate 403 comes
from an L7 rule, a timeout from an L3 or L4 rule**. It is the first hint to
know which part of the policy to fix.

## 🧹 Clean-up

Delete the scratch namespace, which takes the policy with it, and check that
the Pods of the challenge are still there:

```bash
kubectl delete namespace essai-l7 --wait=true --timeout=120s
kubectl -n catalogue get pods
```

```text
namespace "essai-l7" deleted
NAME                      READY   STATUS    RESTARTS   AGE
fiches-65686f97d9-gsqtk   1/1     Running   0          91s
lecteur                   1/1     Running   0          91s
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the
clean-up and then the lab preparation: you get back exactly the starting state
of the challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-filtrer-en-l7-avec-cilium
dsoxlab check k8s-filtrer-en-l7-avec-cilium
```

```text
╭─ Result: k8s-filtrer-en-l7-avec-cilium ─╮
│  0 / 100 pts                            │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests        │
╰─────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for
you, untouched.

## 🎯 The challenge

Your turn, on your own this time: serve an application through a Cilium
Gateway, then protect it with an L7 policy that lets clients read and refuses
writes, through the Gateway as well as from a Pod.

```bash
dsoxlab run k8s-filtrer-en-l7-avec-cilium
dsoxlab challenge k8s-filtrer-en-l7-avec-cilium
```
