# Route with the Gateway API, and repair a route the cluster refuses

The lesson shows a Gateway and an HTTPRoute that send each path to its
application. This course has you read the status the controller writes on
these objects, and adds cases the lesson does not show: a Gateway whose port
matches nothing on the controller's side, a choice by HTTP method and by URL
parameter, a rewritten path, a header added on the way, and a route attached
to a single listener.

You work in a scratch namespace, `essai-gateway`, with a Gateway `guichet`
("counter"), two applications (`salle` and `annexe`: "room" and "annex") and
hosts under `essai.local`. The challenge is about other objects: you will do
it on your own, at the end.

Related page: [Gateway API](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/gateway-api/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-gateway-api-httproute
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The controller is Traefik, with the `traefik` GatewayClass. It listens over
HTTP on port 30080 of every node. To call a host such as
`comptoir.essai.local` without touching DNS, this course uses curl's
`--resolve` option: it tells curl which address to use for that name.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2 and Traefik v3.7.

Create the namespace and two applications. The agnhost image started with
`netexec` answers on several addresses: `/hostname` returns the Pod's name,
and `/header?key=X` returns the value of the header X it received:

```bash
kubectl create namespace essai-gateway
for a in salle annexe; do kubectl run $a --image=registry.k8s.io/e2e-test-images/agnhost:2.53 -n essai-gateway --labels=app=$a -- netexec --http-port=8080 >/dev/null; kubectl expose pod $a --port=80 --target-port=8080 -n essai-gateway >/dev/null; done; kubectl wait --for=condition=Ready pod --all -n essai-gateway --timeout=120s
```

```text
namespace/essai-gateway created
pod/annexe condition met
pod/salle condition met
```

## 🚪 Exercise 1: a listener on a port the controller does not listen on

Create a Gateway with an HTTP listener on port 8000, for all hosts under
`essai.local`:

```bash
cat <<'YAML' | kubectl apply -n essai-gateway -f -
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: guichet
spec:
  gatewayClassName: traefik
  listeners:
    - name: public
      protocol: HTTP
      port: 8000
      hostname: "*.essai.local"
YAML
sleep 5; kubectl get gateway guichet -n essai-gateway
```

```text
gateway.gateway.networking.k8s.io/guichet created
NAME      CLASS     ADDRESS   PROGRAMMED   AGE
guichet   traefik             False        5s
```

`PROGRAMMED` is `False`: the controller could not put the Gateway into
service. The reason is written in the listener's status:

```bash
kubectl get gateway guichet -n essai-gateway -o jsonpath='{range .status.listeners[0].conditions[*]}{.type}={.status} ({.reason}) {.message}{"\n"}{end}'
```

```text
Accepted=False (PortUnavailable) Cannot find entryPoint for Gateway: no matching entryPoint for port 8000 and protocol "HTTP"
```

Traefik ties each listener to one of its entry points (its entrypoints), by
port number. Look at the port its HTTP entry point listens on, and at how the
Service exposes it:

```bash
kubectl -n traefik get deployment traefik -o jsonpath='{range .spec.template.spec.containers[0].args[*]}{@}{"\n"}{end}' | grep 'entryPoints.web.address'; kubectl -n traefik get service traefik -o jsonpath='{range .spec.ports[*]}{.name} {.port} nodePort={.nodePort}{"\n"}{end}'
```

```text
--entryPoints.web.address=:80/tcp
web 80 nodePort=30080
websecure 443 nodePort=30443
```

The `web` entry point listens on port 80 of the container. The Service then
exposes it on port 30080 of the nodes. The listener must carry the entry
point's port, 80, not 30080 nor any other. Fix it:

```bash
kubectl patch gateway guichet -n essai-gateway --type json -p '[{"op":"replace","path":"/spec/listeners/0/port","value":80}]'; kubectl wait --for=condition=Programmed gateway/guichet -n essai-gateway --timeout=60s; kubectl get gateway guichet -n essai-gateway
```

```text
gateway.gateway.networking.k8s.io/guichet patched
gateway.gateway.networking.k8s.io/guichet condition met
NAME      CLASS     ADDRESS   PROGRAMMED   AGE
guichet   traefik             True         5s
```

Remember the move: when a Gateway is not `Programmed`, read
`status.listeners`, not only `status.conditions`.

## 🔀 Exercise 2: choose by method and by parameter

An HTTPRoute does not only choose by path. Create a route that sends `POST`
requests and requests with `?version=2` to `annexe`, and everything else to
`salle`:

```bash
cat <<'YAML' | kubectl apply -n essai-gateway -f -
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: comptoir
spec:
  parentRefs:
    - name: guichet
  hostnames: [comptoir.essai.local]
  rules:
    - matches:
        - method: POST
      backendRefs:
        - name: annexe
          port: 80
    - matches:
        - queryParams:
            - name: version
              value: "2"
      backendRefs:
        - name: annexe
          port: 80
    - backendRefs:
        - name: salle
          port: 80
YAML
sleep 3
```

```text
httproute.gateway.networking.k8s.io/comptoir created
```

Send four requests, and read the name of the application that answers:

```bash
R='--resolve comptoir.essai.local:30080:127.0.0.1 http://comptoir.essai.local:30080'; for essai in 'GET /hostname' 'POST /hostname' 'GET /hostname?version=2' 'GET /hostname?version=3'; do set -- $essai; printf '%-26s -> ' "$essai"; curl -s -X $1 $R$2; echo; done
```

```text
GET /hostname              -> salle
POST /hostname             -> annexe
GET /hostname?version=2    -> annexe
GET /hostname?version=3    -> salle
```

`POST` and `version=2` go to `annexe`. `version=3` matches no condition and
falls to the last rule, which has none. A rule without `matches` takes
whatever the others leave: it is the route's default.

## ✏️ Exercise 3: rewrite the path before passing it on

Clients still call an old path, `/qui-repond` ("who-answers"), that the
application does not know. The `URLRewrite` filter replaces it with
`/hostname` before passing the request on:

```bash
cat <<'YAML' | kubectl apply -n essai-gateway -f -
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: ancien-chemin
spec:
  parentRefs:
    - name: guichet
  hostnames: [ancien.essai.local]
  rules:
    - matches:
        - path: {type: PathPrefix, value: /qui-repond}
      filters:
        - type: URLRewrite
          urlRewrite:
            path:
              type: ReplacePrefixMatch
              replacePrefixMatch: /hostname
      backendRefs:
        - name: salle
          port: 80
YAML
sleep 3; curl -s -w '  [%{http_code}]\n' --resolve ancien.essai.local:30080:127.0.0.1 http://ancien.essai.local:30080/qui-repond
```

```text
httproute.gateway.networking.k8s.io/ancien-chemin created
salle  [200]
```

The client asked for `/qui-repond`, the application received `/hostname`, and
the client does not see the change. With `ReplacePrefixMatch`, only the
matching start is replaced: `/qui-repond/x` would become `/hostname/x`.

## 🏷️ Exercise 4: add a header on the way

Add a rule for `/header` to the route, with the `RequestHeaderModifier`
filter that sets the `X-Equipe: accueil` header on every request. The call
then asks the application for the value it received:

```bash
kubectl patch httproute ancien-chemin -n essai-gateway --type json -p '[{"op":"add","path":"/spec/rules/-","value":{"matches":[{"path":{"type":"PathPrefix","value":"/header"}}],"filters":[{"type":"RequestHeaderModifier","requestHeaderModifier":{"set":[{"name":"X-Equipe","value":"accueil"}]}}],"backendRefs":[{"name":"salle","port":80}]}}]'; sleep 3; curl -s --resolve ancien.essai.local:30080:127.0.0.1 'http://ancien.essai.local:30080/header?key=X-Equipe'; echo
```

```text
httproute.gateway.networking.k8s.io/ancien-chemin patched
accueil
```

The application received the header added by the controller. This is useful
to tell the backend where the request comes from, without touching the client.

## 🎚️ Exercise 5: attach to a single listener

Add a second listener to the Gateway, `interne`, for hosts under
`interne.local`:

```bash
kubectl patch gateway guichet -n essai-gateway --type json -p '[{"op":"add","path":"/spec/listeners/-","value":{"name":"interne","protocol":"HTTP","port":80,"hostname":"*.interne.local"}}]'; kubectl wait --for=condition=Programmed gateway/guichet -n essai-gateway --timeout=60s
```

```text
gateway.gateway.networking.k8s.io/guichet patched
gateway.gateway.networking.k8s.io/guichet condition met
```

Create a route for `bureau.interne.local`, but attach it by mistake to the
`public` listener with `sectionName`, then read its status:

```bash
cat <<'YAML' | kubectl apply -n essai-gateway -f -
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: bureau
spec:
  parentRefs:
    - name: guichet
      sectionName: public
  hostnames: [bureau.interne.local]
  rules:
    - backendRefs:
        - name: salle
          port: 80
YAML
sleep 3; kubectl get httproute bureau -n essai-gateway -o jsonpath='{range .status.parents[0].conditions[*]}{.type}={.status} ({.reason}){"\n"}{end}'
```

```text
httproute.gateway.networking.k8s.io/bureau created
Accepted=False (NoMatchingListenerHostname)
ResolvedRefs=True (ResolvedRefs)
```

`Accepted=False`, reason `NoMatchingListenerHostname`: the `public` listener
only accepts `*.essai.local`, and the route's name does not fit. A refused
route breaks nothing else, it is simply not served. Attach it to the right
listener:

```bash
kubectl patch httproute bureau -n essai-gateway --type json -p '[{"op":"replace","path":"/spec/parentRefs/0/sectionName","value":"interne"}]'; sleep 3; kubectl get httproute bureau -n essai-gateway -o jsonpath='{range .status.parents[0].conditions[*]}{.type}={.status} ({.reason}){"\n"}{end}'; curl -s --resolve bureau.interne.local:30080:127.0.0.1 "http://bureau.interne.local:30080/hostname"; echo
```

```text
httproute.gateway.networking.k8s.io/bureau patched
Accepted=True (Accepted)
ResolvedRefs=True (ResolvedRefs)
salle
```

The route is accepted and `salle` answers. Without `sectionName`, a route
attaches to every listener of the Gateway that accepts it. With it, you choose
the way in.

## 🧹 Clean-up

Delete the scratch namespace. The Gateway, the routes and the applications go
with it:

```bash
kubectl delete namespace essai-gateway
```

```text
namespace "essai-gateway" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-gateway-api-httproute
dsoxlab check cka-gateway-api-httproute
```

```text
╭─ Result: cka-gateway-api-httproute ─╮
│  0 / 100 pts                        │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests    │
╰─────────────────────────────────────╯
```

0 out of 6: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a Gateway to put into service, two
applications to route by path, and a refused route to get accepted.

```bash
dsoxlab run cka-gateway-api-httproute
dsoxlab challenge cka-gateway-api-httproute
```
