# Route two applications on a single host, and check that each one gets its own

The lesson shows an Ingress that sends each path to its application. This
course shows what the controller really does with the rules, with Traefik,
the controller installed on the lab's cluster: `Exact` versus `Prefix`, a
prefix that covers more than you think, the longest path winning, a default
backend that Traefik ignores in one specific case, and an Ingress without a
class.

You work in a scratch namespace, `essai-ingress`, with three applications
(`boutique`, `promo`, `secours`: "shop", "sale", "fallback") and the host
`magasin.local`. The challenge is about other objects: you will do it on your
own, at the end.

Related page: [Ingress](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/ingress/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-ingress-path-routing
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

Traefik listens over HTTP on port 30080 of every node. To call a host such as
`magasin.local` without touching DNS, this course uses curl's `--resolve`
option: it tells curl which address to use for that name.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2 and Traefik v3.7.

Create the namespace and three applications. Each one answers with its own
name (`serve-hostname` from the agnhost image), which shows who answered:

```bash
kubectl create namespace essai-ingress
for a in boutique promo secours; do kubectl run $a --image=registry.k8s.io/e2e-test-images/agnhost:2.53 -n essai-ingress --labels=app=$a -- serve-hostname --port=8080 >/dev/null; kubectl expose pod $a --port=80 --target-port=8080 -n essai-ingress >/dev/null; done; kubectl wait --for=condition=Ready pod --all -n essai-ingress --timeout=120s; kubectl get services -n essai-ingress
```

```text
namespace/essai-ingress created
pod/boutique condition met
pod/promo condition met
pod/secours condition met
NAME       TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)   AGE
boutique   ClusterIP   10.103.246.157   <none>        80/TCP    1s
promo      ClusterIP   10.98.110.214    <none>        80/TCP    1s
secours    ClusterIP   10.106.202.191   <none>        80/TCP    1s
```

Check the available Ingress class:

```bash
kubectl get ingressclass
```

```text
NAME      CONTROLLER                      PARAMETERS   AGE
traefik   traefik.io/ingress-controller   <none>       5m58s
```

## 🎯 Exercise 1: Exact or Prefix

Create an Ingress that sends exactly `/boutique` to the `boutique`
application:

```bash
cat <<'YAML' | kubectl apply -n essai-ingress -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: magasin
spec:
  ingressClassName: traefik
  rules:
    - host: magasin.local
      http:
        paths:
          - path: /boutique
            pathType: Exact
            backend:
              service: {name: boutique, port: {number: 80}}
YAML
```

```text
ingress.networking.k8s.io/magasin created
```

Call three paths. The command prints the HTTP code of each one:

```bash
sleep 3; for p in /boutique /boutique/ /boutique/panier; do curl -s -o /dev/null -w '%{http_code} ' --resolve magasin.local:30080:127.0.0.1 "http://magasin.local:30080$p";  echo " <- $p"; done
```

```text
200  <- /boutique
404  <- /boutique/
404  <- /boutique/panier
```

With `pathType: Exact`, only `/boutique` goes through. `/boutique/` (with the
trailing slash) and `/boutique/panier` return 404. A client or a browser that
adds a trailing slash therefore lands on an error.

## 🧩 Exercise 2: a prefix covers more than you think

Switch the rule to `Prefix` and call four paths, including `/boutiques`:

```bash
kubectl patch ingress magasin -n essai-ingress --type json -p '[{"op":"replace","path":"/spec/rules/0/http/paths/0/pathType","value":"Prefix"}]'; sleep 3; for p in /boutique /boutique/ /boutique/panier /boutiques; do curl -s -o /dev/null -w '%{http_code} ' --resolve magasin.local:30080:127.0.0.1 "http://magasin.local:30080$p";  echo " <- $p"; done
```

```text
ingress.networking.k8s.io/magasin patched
200  <- /boutique
200  <- /boutique/
200  <- /boutique/panier
200  <- /boutiques
```

The first three go through, that is what `Prefix` is for. The fourth one too.
Yet the Kubernetes specification compares a prefix segment by segment (the
pieces between two `/`): `/boutique` should not cover `/boutiques`. Traefik,
here, compares characters. The result therefore depends on the controller. If
another application must answer on `/boutiques`, declare its path explicitly
rather than relying on the specification.

## 📏 Exercise 3: the longest path wins

Add a second, longer path that starts like the first one:

```bash
kubectl patch ingress magasin -n essai-ingress --type json -p '[{"op":"add","path":"/spec/rules/0/http/paths/-","value":{"path":"/boutique/promo","pathType":"Prefix","backend":{"service":{"name":"promo","port":{"number":80}}}}}]'; sleep 3
```

```text
ingress.networking.k8s.io/magasin patched
```

Call three paths. This time, the command prints the name of the application
that answers:

```bash
for p in /boutique/panier /boutique/promo /boutique/promo/noel; do printf '%s -> ' $p; curl -s --resolve magasin.local:30080:127.0.0.1 "http://magasin.local:30080$p"; echo; done
```

```text
/boutique/panier -> boutique
/boutique/promo -> promo
/boutique/promo/noel -> promo
```

`/boutique/promo` and everything below it go to `promo`. The rest of
`/boutique` still goes to `boutique`. When two prefixes match, the longer one
wins, even when it is declared after the other one in the Ingress.

## 🛟 Exercise 4: a default for everything else

For now, a path that matches no rule returns 404:

```bash
for p in /inconnu /; do curl -s -o /dev/null -w '%{http_code} ' --resolve magasin.local:30080:127.0.0.1 "http://magasin.local:30080$p";  echo " <- $p"; done
```

```text
404  <- /inconnu
404  <- /
```

The `spec.defaultBackend` field of an Ingress names the application that
receives everything no rule takes. Add it to `magasin`:

```bash
kubectl patch ingress magasin -n essai-ingress --type merge -p '{"spec":{"defaultBackend":{"service":{"name":"secours","port":{"number":80}}}}}'; sleep 3; for p in /inconnu /; do printf '%s -> ' $p; curl -s --resolve magasin.local:30080:127.0.0.1 "http://magasin.local:30080$p"; echo; done
```

```text
ingress.networking.k8s.io/magasin patched
/inconnu -> 404 page not found

/ -> 404 page not found
```

Nothing changes: `404 page not found` is Traefik's page. On this cluster,
Traefik ignores the `defaultBackend` of an Ingress that also has rules. It
only uses it in an Ingress that has nothing but this field. Remove it from
`magasin` and create an Ingress `secours` that declares only that:

```bash
kubectl patch ingress magasin -n essai-ingress --type json -p '[{"op":"remove","path":"/spec/defaultBackend"}]'
cat <<'YAML' | kubectl apply -n essai-ingress -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: secours
spec:
  ingressClassName: traefik
  defaultBackend:
    service: {name: secours, port: {number: 80}}
YAML
```

```text
ingress.networking.k8s.io/magasin patched
ingress.networking.k8s.io/secours created
```

Call again, including another host:

```bash
sleep 5; for p in /boutique/panier /inconnu /; do printf '%s -> ' $p; curl -s --resolve magasin.local:30080:127.0.0.1 "http://magasin.local:30080$p"; echo; done; printf 'autre.local/ -> '; curl -s --resolve autre.local:30080:127.0.0.1 "http://autre.local:30080/"; echo
```

```text
/boutique/panier -> boutique
/inconnu -> secours
/ -> secours
autre.local/ -> secours
```

The rules of `magasin` keep priority (`/boutique/panier` goes to `boutique`),
and `secours` takes everything else, even for a host declared nowhere. An
Ingress accepted by the API is therefore no proof: only a call shows what the
controller made of it.

## 🏷️ Exercise 5: an Ingress without a class

An Ingress class can be marked as the default class, with an annotation. Read
those of `traefik`:

```bash
kubectl get ingressclass traefik -o jsonpath='{.metadata.annotations}{"\n"}'
```

```text
{"ingressclass.kubernetes.io/is-default-class":"false","meta.helm.sh/release-name":"traefik","meta.helm.sh/release-namespace":"traefik"}
```

`is-default-class` is `false`: Traefik is not the default class. Create an
Ingress without `ingressClassName`, then read its class and call it:

```bash
cat <<'YAML' | kubectl apply -n essai-ingress -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: sans-classe
spec:
  rules:
    - host: sans-classe.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service: {name: promo, port: {number: 80}}
YAML
sleep 3; kubectl get ingress sans-classe -n essai-ingress -o jsonpath='{.spec.ingressClassName}{"\n"}'; curl -s -o /dev/null -w '%{http_code}\n' --resolve sans-classe.local:30080:127.0.0.1 http://sans-classe.local:30080/
```

```text
ingress.networking.k8s.io/sans-classe created

200
```

The empty line is the Ingress's class: it has none. Traefik serves it anyway
(200). So do not rely on a missing class to keep an Ingress ignored. On a
cluster with several controllers, always write `ingressClassName`.

## 🧹 Clean-up

Delete the scratch namespace. The Ingresses, Services and Pods go with it:

```bash
kubectl delete namespace essai-ingress
```

```text
namespace "essai-ingress" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-ingress-path-routing
dsoxlab check cka-ingress-path-routing
```

```text
╭─ Result: cka-ingress-path-routing ─╮
│  0 / 100 pts                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests   │
╰────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: two applications to route on a single
host, and the proof that each one receives its own requests.

```bash
dsoxlab run cka-ingress-path-routing
dsoxlab challenge cka-ingress-path-routing
```
