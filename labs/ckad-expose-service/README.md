# Expose an application with a Service

The Pods of an application change IP address every time they are replaced.
The other applications of the cluster therefore cannot reach them by their
address. A **Service** gives them a fixed **name** and **address**, and spreads
the requests across the Pods it selects. The lesson creates a Service with
`kubectl expose` and reaches it by its name. This course makes you write a
Service by hand, tell apart two Services with the same name in two namespaces,
and recognise two failures: a wrong target port, and one Pod too many in the
selection.

You work in two scratch namespaces, `essai-expose` and `essai-voisin`, with an
`annuaire` application. The challenge will ask you to expose another
application: you will do it on your own, at the end.

Related page: [Kubernetes Services](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/services/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-expose-service
```

You are now connected to `k8s-cp.lab`, the node that drives the kubeadm
cluster (the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 20 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: an application, without a Service

Create the scratch namespace, then the `annuaire` application, in two Pods.
Their container serves the text `annuaire` on port 8080. This port has a
**name**, `http`: it will be used in exercise 5.

```bash
kubectl create namespace essai-expose
cat <<'YAML' | kubectl apply -n essai-expose -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: annuaire
spec:
  replicas: 2
  selector:
    matchLabels:
      app: annuaire
  template:
    metadata:
      labels:
        app: annuaire
    spec:
      containers:
        - name: web
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "mkdir -p /www && echo annuaire > /www/index.html && exec httpd -f -p 8080 -h /www"]
          ports:
            - name: http
              containerPort: 8080
YAML
```

```text
namespace/essai-expose created
deployment.apps/annuaire created
```

Wait until it is ready, then look at its Pods with their address:

```bash
kubectl rollout status deployment/annuaire -n essai-expose --timeout=120s | tail -1
kubectl get pods -n essai-expose -o wide
```

```text
deployment "annuaire" successfully rolled out
NAME                       READY   STATUS    RESTARTS   AGE   IP              NODE         NOMINATED NODE   READINESS GATES
annuaire-59d6c5c5d-t5h74   1/1     Running   0          1s    10.244.38.91    k8s-w1.lab   <none>           <none>
annuaire-59d6c5c5d-xg58z   1/1     Running   0          1s    10.244.163.12   k8s-cp.lab   <none>           <none>
```

Each Pod has its own address, on a different node. To query the application
from inside the cluster, create a `sonde` Pod that only sleeps:

```bash
kubectl run sonde \
  --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 \
  --restart=Never -n essai-expose -- sleep 3600
kubectl wait --for=condition=Ready pod/sonde -n essai-expose --timeout=60s
```

```text
pod/sonde created
pod/sonde condition met
```

## 📚 Exercise 2: write the Service by hand

The lesson creates its Service with `kubectl expose`. Write this one in a
file: you then see the three fields that matter.

```bash
cat > ~/essai-annuaire-svc.yaml <<'YAML'
apiVersion: v1
kind: Service
metadata:
  name: annuaire
  namespace: essai-expose
spec:
  selector:
    app: annuaire
  ports:
    - port: 80
      targetPort: 8080
YAML
kubectl apply -f ~/essai-annuaire-svc.yaml
kubectl get service annuaire -n essai-expose
kubectl get endpointslices -n essai-expose -l kubernetes.io/service-name=annuaire
```

```text
service/annuaire created
NAME       TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE
annuaire   ClusterIP   10.110.40.62   <none>        80/TCP    0s
NAME             ADDRESSTYPE   PORTS   ENDPOINTS                    AGE
annuaire-lrgrj   IPv4          8080    10.244.163.12,10.244.38.91   0s
```

`selector` says which Pods the Service picks: those that carry
`app=annuaire`. `port` is the port of the Service, the one you call.
`targetPort` is the port of the containers, where it sends the requests.
Without a `type`, the Service is a `ClusterIP`: reachable only from inside the
cluster. The two endpoint addresses are those of the Pods of exercise 1. Query
it by its name:

```bash
kubectl exec sonde -n essai-expose -- wget -qO- -T 2 http://annuaire
```

```text
annuaire
```

## 📚 Exercise 3: two Services with the same name

A Service name is only unique inside its namespace. Create a second namespace,
with an `annuaire` application that serves `voisin`, and the same Service:

```bash
kubectl create namespace essai-voisin
cat <<'YAML' | kubectl apply -n essai-voisin -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: annuaire
spec:
  replicas: 2
  selector:
    matchLabels:
      app: annuaire
  template:
    metadata:
      labels:
        app: annuaire
    spec:
      containers:
        - name: web
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "mkdir -p /www && echo voisin > /www/index.html && exec httpd -f -p 8080 -h /www"]
          ports:
            - name: http
              containerPort: 8080
YAML
sed "s/namespace: essai-expose/namespace: essai-voisin/" ~/essai-annuaire-svc.yaml | kubectl apply -f -
kubectl rollout status deployment/annuaire -n essai-voisin --timeout=120s | tail -1
kubectl get services -A --field-selector metadata.name=annuaire
```

```text title="Excerpt of the output"
namespace/essai-voisin created
deployment.apps/annuaire created
service/annuaire created
deployment "annuaire" successfully rolled out
NAMESPACE      NAME       TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
essai-expose   annuaire   ClusterIP   10.110.40.62    <none>        80/TCP    7s
essai-voisin   annuaire   ClusterIP   10.100.94.251   <none>        80/TCP    4s
```

Two `annuaire` Services, two addresses. From the probe, query the short name,
then the name followed by the namespace:

```bash
kubectl exec sonde -n essai-expose -- wget -qO- -T 2 http://annuaire
kubectl exec sonde -n essai-expose -- wget -qO- -T 2 http://annuaire.essai-voisin
```

```text
annuaire
voisin
```

The short name leads to the Service of the probe's namespace. To reach the
other one, you must add its namespace. The reason is in the Pod's DNS
configuration:

```bash
kubectl exec sonde -n essai-expose -- cat /etc/resolv.conf
```

```text
search essai-expose.svc.cluster.local svc.cluster.local cluster.local lab
nameserver 10.96.0.10
options ndots:5
```

The `search` line lists the suffixes tried in order. `annuaire` first becomes
`annuaire.essai-expose.svc.cluster.local`: the Pod's namespace comes first.
`annuaire.essai-voisin` becomes `annuaire.essai-voisin.svc.cluster.local`
with the second suffix.

## 📚 Exercise 4: a target port that leads nowhere

Create a third Service, with a wrong target port, `9090`, while the containers
listen on 8080. Wait a few seconds for the Service to be in place, then query
it:

```bash
kubectl expose deployment annuaire --name=annuaire-faux --port=80 --target-port=9090 -n essai-expose
kubectl get endpointslices -n essai-expose -l kubernetes.io/service-name=annuaire-faux
sleep 3
kubectl exec sonde -n essai-expose -- wget -qO- -T 3 http://annuaire-faux
```

```text
service/annuaire-faux exposed
NAME                  ADDRESSTYPE   PORTS   ENDPOINTS                    AGE
annuaire-faux-jffnm   IPv4          9090    10.244.163.12,10.244.38.91   0s
wget: can't connect to remote host (10.98.214.179): Connection refused
command terminated with exit code 1
```

The endpoints are there, on port `9090`: the selector is right, Kubernetes
found the Pods. Yet nothing checks that they listen on that port.
`Connection refused` means the request reached the Pod, and nothing listens on
that port there. Keep the difference in mind: **no endpoint**, the selector is
wrong; **endpoints, and a refused connection**, it is the target port. Delete
this Service:

```bash
kubectl delete service annuaire-faux -n essai-expose
```

```text
service "annuaire-faux" deleted from essai-expose namespace
```

## 📚 Exercise 5: target a port by its name

The container's port is called `http`:

```bash
kubectl get deployment annuaire -n essai-expose -o jsonpath='{.spec.template.spec.containers[0].ports[0]}{"\n"}'
```

```text
{"containerPort":8080,"name":"http","protocol":"TCP"}
```

The target port of a Service can give this name instead of the number:

```bash
kubectl expose deployment annuaire --name=annuaire-nomme --port=80 --target-port=http -n essai-expose
kubectl get service annuaire-nomme -n essai-expose -o jsonpath='{.spec.ports[0].targetPort}{"\n"}'
sleep 3; kubectl exec sonde -n essai-expose -- wget -qO- -T 2 http://annuaire-nomme
```

```text
service/annuaire-nomme exposed
http
annuaire
```

The benefit: if the application changes port one day, only the Deployment
needs changing. The Service, which targets `http`, follows without any edit.

## 📚 Exercise 6: one Pod too many in the Service

The `annuaire` Service has two endpoints, the two Pods of the application:

```bash
kubectl get endpointslices -n essai-expose -l kubernetes.io/service-name=annuaire
```

```text
NAME             ADDRESSTYPE   PORTS   ENDPOINTS                    AGE
annuaire-lrgrj   IPv4          8080    10.244.163.12,10.244.38.91   19s
```

The Service picks **every** Pod of the namespace that carries `app=annuaire`,
even those that are not part of the application. Give this label to the
probe:

```bash
kubectl label pod sonde app=annuaire -n essai-expose
sleep 3; kubectl get endpointslices -n essai-expose -l kubernetes.io/service-name=annuaire
```

```text
pod/sonde labeled
NAME             ADDRESSTYPE   PORTS   ENDPOINTS                                 AGE
annuaire-lrgrj   IPv4          8080    10.244.163.12,10.244.38.91,10.244.38.74   22s
```

The probe became a third endpoint. Yet it serves nothing on port 8080. Send
six requests (`|| echo ECHEC` reports each failed request):

```bash
for i in 1 2 3 4 5 6; do kubectl exec sonde -n essai-expose -- wget -qO- -T 2 "http://annuaire" || echo ECHEC; done
```

```text
wget: can't connect to remote host (10.110.40.62): Connection refused
command terminated with exit code 1
ECHEC
wget: can't connect to remote host (10.110.40.62): Connection refused
command terminated with exit code 1
ECHEC
annuaire
annuaire
annuaire
wget: can't connect to remote host (10.110.40.62): Connection refused
command terminated with exit code 1
ECHEC
```

Three requests failed: those the Service sent to the probe. The split is
random, so you may see more or fewer. Remove the label (the dash after the key
erases it), then start again:

```bash
kubectl label pod sonde app- -n essai-expose
sleep 3; for i in 1 2 3 4 5 6; do kubectl exec sonde -n essai-expose -- wget -qO- -T 2 "http://annuaire" || echo ECHEC; done
```

```text
pod/sonde unlabeled
annuaire
annuaire
annuaire
annuaire
annuaire
annuaire
```

Six answers out of six. Before concluding that a Service works, count its
endpoints: there must be as many as the application has Pods.

## 🧹 Clean up

First delete what you created during the exercises: both scratch namespaces
and the Service file.

```bash
kubectl delete namespace essai-expose essai-voisin
rm ~/essai-annuaire-svc.yaml
```

```text
namespace "essai-expose" deleted
namespace "essai-voisin" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset ckad-expose-service
dsoxlab check ckad-expose-service
```

```text
╭─── Result: ckad-expose-service ────╮
│  0 / 100 pts                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/11 tests  │
╰────────────────────────────────────╯
```

0 out of 11: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a service in four copies, each one
answering its own name, reachable by the other applications under a stable
name and port.

```bash
dsoxlab run ckad-expose-service
dsoxlab challenge ckad-expose-service
```
