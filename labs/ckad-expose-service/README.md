# Expose an application with a Service

The Pods of an application change IP address each time they are replaced. The
other applications of the cluster therefore cannot reach them by address. A
**Service** gives them a fixed **name** and **address**, and spreads the
requests over the Pods it selects. In this course, you create a Service with
`kubectl expose`, you reach it by its different names, you see what happens
when its target port is wrong, and when one Pod too many enters its selection.

You work in a scratch namespace, `essai-expose`, with an `annuaire`
application. The challenge will ask you to expose another application: you will
do it on your own, at the end.

Related page: [Kubernetes Services](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/services/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-expose-service
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: an application, without a Service

Create the scratch namespace:

```bash
kubectl create namespace essai-expose
```

```text
namespace/essai-expose created
```

The `annuaire` application runs in two Pods. Their container serves the text
`annuaire` on port 8080. That port has a **name**, `http`: it will be used in
exercise 5.

```bash
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
          command: ["sh", "-c", "echo annuaire > /tmp/index.html && httpd -f -p 8080 -h /tmp"]
          ports:
            - name: http
              containerPort: 8080
YAML
```

```text
deployment.apps/annuaire created
```

Wait until it is ready, then look at its Pods with their address (`-o wide`):

```bash
kubectl rollout status deployment/annuaire -n essai-expose --timeout=120s | tail -1
kubectl get pods -n essai-expose -o wide
```

```text
deployment "annuaire" successfully rolled out
NAME                       READY   STATUS    RESTARTS   AGE   IP              NODE         NOMINATED NODE   READINESS GATES
annuaire-78f54cb8c-6lddp   1/1     Running   0          1s    10.244.163.38   k8s-cp.lab   <none>           <none>
annuaire-78f54cb8c-bdsxp   1/1     Running   0          1s    10.244.38.106   k8s-w1.lab   <none>           <none>
```

Each Pod has its own address, on a different node. These addresses change as
soon as a Pod is replaced. To query the application from inside the cluster,
create a `sonde` Pod that only sleeps:

```bash
kubectl run sonde --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --restart=Never -n essai-expose -- sleep 3600
kubectl wait --for=condition=Ready pod/sonde -n essai-expose --timeout=60s
```

```text
pod/sonde created
pod/sonde condition met
```

## 📚 Exercise 2: create the Service with kubectl expose

`kubectl expose` creates a Service for a Deployment, reusing its selector. Two
ports matter:

- `--port`: the port of the **Service**, the one other applications call;
- `--target-port`: the port of the **containers**, where the Service sends the
  requests.

```bash
kubectl expose deployment annuaire --port=80 --target-port=8080 -n essai-expose
kubectl get service annuaire -n essai-expose
```

```text
service/annuaire exposed
NAME       TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
annuaire   ClusterIP   10.106.114.47   <none>        80/TCP    0s
```

The Service is of type `ClusterIP`: it can only be reached from inside the
cluster, at address `10.106.114.47`, on port 80. `describe` shows the rest
(`grep` keeps only the useful lines):

```bash
kubectl describe service annuaire -n essai-expose | grep -E '^(Selector|Type|IP|Port|TargetPort|Endpoints):'
```

```text
Selector:                 app=annuaire
Type:                     ClusterIP
IP:                       10.106.114.47
Port:                     <unset>  80/TCP
TargetPort:               8080/TCP
Endpoints:                10.244.38.106:8080,10.244.163.38:8080
```

`Selector` says which Pods the Service picks: those carrying `app=annuaire`.
`Endpoints` lists their addresses, with the target port: these are the two Pods
of exercise 1.

## 📚 Exercise 3: reach the Service by its name

The cluster DNS gives a name to every Service. From a Pod in the **same**
namespace, the short name is enough:

```bash
kubectl exec sonde -n essai-expose -- wget -qO- -T 2 http://annuaire
```

```text
annuaire
```

From another namespace, you must add the namespace, or give the full name:

```bash
kubectl exec sonde -n essai-expose -- wget -qO- -T 2 http://annuaire.essai-expose
kubectl exec sonde -n essai-expose -- wget -qO- -T 2 http://annuaire.essai-expose.svc.cluster.local
```

```text
annuaire
annuaire
```

Port 80 does not show in the address: it is the default HTTP port, and it is
the Service port. `nslookup` shows which address the name points to:

```bash
kubectl exec sonde -n essai-expose -- nslookup annuaire.essai-expose.svc.cluster.local
```

```text
Server:		10.96.0.10
Address:	10.96.0.10:53


Name:	annuaire.essai-expose.svc.cluster.local
Address: 10.106.114.47
```

The name points to the fixed address of the Service (`10.106.114.47`), never to
the address of a Pod.

## 📚 Exercise 4: a target port that leads nowhere

Create a second Service, with a wrong target port, `9090`, while the containers
listen on 8080:

```bash
kubectl expose deployment annuaire --name=annuaire-faux --port=80 --target-port=9090 -n essai-expose
kubectl get endpointslices -n essai-expose -l kubernetes.io/service-name=annuaire-faux
```

```text
service/annuaire-faux exposed
NAME                  ADDRESSTYPE   PORTS   ENDPOINTS                     AGE
annuaire-faux-bfnzx   IPv4          9090    10.244.163.38,10.244.38.106   0s
```

The endpoints are there, but on port `9090`. The selector is right, so
Kubernetes did find the Pods. Yet nothing checks that they listen on that port:

```bash
kubectl exec sonde -n essai-expose -- wget -qO- -T 3 http://annuaire-faux
```

```text
wget: download timed out
command terminated with exit code 1
```

The request goes nowhere. Remember the difference: **no endpoint** means the
selector is wrong. **Endpoints but no answer** is often the target port. Delete
this Service:

```bash
kubectl delete service annuaire-faux -n essai-expose
```

```text
service "annuaire-faux" deleted from essai-expose namespace
```

## 📚 Exercise 5: target a port by its name

The container port is called `http`:

```bash
kubectl get deployment annuaire -n essai-expose -o jsonpath='{.spec.template.spec.containers[0].ports[0]}{"\n"}'
```

```text
{"containerPort":8080,"name":"http","protocol":"TCP"}
```

The target port of a Service can give that name instead of the number:

```bash
kubectl expose deployment annuaire --name=annuaire-nomme --port=80 --target-port=http -n essai-expose
kubectl get service annuaire-nomme -n essai-expose -o jsonpath='{.spec.ports[0].targetPort}{"\n"}'
sleep 2; kubectl exec sonde -n essai-expose -- wget -qO- -T 2 http://annuaire-nomme
```

```text
service/annuaire-nomme exposed
http
annuaire
```

The benefit: if the application ever changes port, only the Deployment needs
changing. The Service, which targets `http`, follows with no edit.

## 📚 Exercise 6: one Pod too many in the Service

The `annuaire` Service has two endpoints, the two Pods of the application:

```bash
kubectl get endpointslices -n essai-expose -l kubernetes.io/service-name=annuaire
```

```text
NAME             ADDRESSTYPE   PORTS   ENDPOINTS                     AGE
annuaire-lr9v8   IPv4          8080    10.244.38.106,10.244.163.38   7s
```

The Service picks **every** Pod of the namespace carrying `app=annuaire`, even
those that are not part of the application. Give that label to the probe:

```bash
kubectl label pod sonde app=annuaire -n essai-expose
sleep 3; kubectl get endpointslices -n essai-expose -l kubernetes.io/service-name=annuaire
```

```text
pod/sonde labeled
NAME             ADDRESSTYPE   PORTS   ENDPOINTS                                   AGE
annuaire-lr9v8   IPv4          8080    10.244.38.106,10.244.163.38,10.244.38.107   10s
```

The probe became a third endpoint. Yet it serves nothing on port 8080. Send six
requests (`|| echo ECHEC` flags each failed request):

```bash
for i in 1 2 3 4 5 6; do kubectl exec sonde -n essai-expose -- wget -qO- -T 2 'http://annuaire' || echo ECHEC; done
```

```text
annuaire
wget: can't connect to remote host (10.106.114.47): Connection refused
command terminated with exit code 1
ECHEC
annuaire
annuaire
annuaire
annuaire
```

One request failed: the one the Service sent to the probe. The spreading is
random, so you may see more or fewer. Remove the label (the dash after the key
deletes it), then try again:

```bash
kubectl label pod sonde app- -n essai-expose
sleep 3; for i in 1 2 3 4 5 6; do kubectl exec sonde -n essai-expose -- wget -qO- -T 2 'http://annuaire' || echo ECHEC; done
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

Delete the scratch namespace, with everything in it:

```bash
kubectl delete namespace essai-expose
```

```text
namespace "essai-expose" deleted
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

Your turn, on your own this time: a web server in three copies, each one
answering its own name, reachable by the other applications under a stable
name.

```bash
dsoxlab run ckad-expose-service
dsoxlab challenge ckad-expose-service
```
