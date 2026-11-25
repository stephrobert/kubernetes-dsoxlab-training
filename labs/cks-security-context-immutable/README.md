# Make a container immutable without bringing it down

The lesson shows how to lock a container down: read-only root, kernel
capabilities dropped. This course focuses on the file system and
capabilities, and adds cases the lesson does not show: finding, through its
errors, where an application writes, giving it back that single directory,
dropping every capability then giving back just one, and a kernel setting
(sysctl) that the kubelet refuses.

You work in a scratch namespace, `essai-fige` ("test-frozen"), with an Apache
server (`httpd`) and busybox Pods. The challenge is about another application:
you will do it on your own, at the end.

Related page: [Security Context](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/security-context/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-security-context-immutable
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2 and httpd 2.4.66.

## 💥 Exercise 1: a read-only root, and the application falls over

Create the namespace and an Apache Pod with `readOnlyRootFilesystem: true`,
without any volume. Wait 15 seconds, then read the end of its logs:

```bash
kubectl create namespace essai-fige; cat <<YAML | kubectl apply -n essai-fige -f -
apiVersion: v1
kind: Pod
metadata:
  name: apache
spec:
  containers:
    - name: apache
      image: httpd:2.4.66
      securityContext:
        readOnlyRootFilesystem: true
      volumeMounts: []
  volumes: []
YAML
sleep 15; kubectl get pod apache -n essai-fige; kubectl logs apache -n essai-fige --tail=3
```

```text
namespace/essai-fige created
pod/apache created
NAME     READY   STATUS             RESTARTS     AGE
apache   0/1     CrashLoopBackOff   1 (7s ago)   15s
AH00558: httpd: Could not reliably determine the server's fully qualified domain name, using 10.244.38.123. Set the 'ServerName' directive globally to suppress this message
[Sat Nov 21 03:09:06.067497 2026] [core:error] [pid 1:tid 1] (30)Read-only file system: AH00099: could not create /usr/local/apache2/logs/httpd.pid.G6A2yI
[Sat Nov 21 03:09:06.067542 2026] [core:error] [pid 1:tid 1] AH00100: httpd: could not log pid to file /usr/local/apache2/logs/httpd.pid
```

The Pod restarts in a loop. The logs name the file httpd could not create:
`/usr/local/apache2/logs/httpd.pid`, the record of its process number. This
is the method for any application: close the root, then read what fails.

## 📂 Exercise 2: give the application back the only directory it writes to

Recreate the Pod with an `emptyDir` volume mounted on
`/usr/local/apache2/logs`. Once it is ready, try to write elsewhere, then list
the directory you gave back:

```bash
kubectl delete pod apache -n essai-fige; cat <<YAML | kubectl apply -n essai-fige -f -
apiVersion: v1
kind: Pod
metadata:
  name: apache
spec:
  containers:
    - name: apache
      image: httpd:2.4.66
      securityContext:
        readOnlyRootFilesystem: true
      volumeMounts: [{name: journaux, mountPath: /usr/local/apache2/logs}]
  volumes: [{name: journaux, emptyDir: {}}]
YAML
kubectl wait --for=condition=Ready pod/apache -n essai-fige --timeout=120s; kubectl exec apache -n essai-fige -- sh -c 'touch /usr/local/apache2/htdocs/x; echo code $?; ls /usr/local/apache2/logs'
```

```text
pod "apache" deleted from essai-fige namespace
pod/apache created
pod/apache condition met
code 1
touch: cannot touch '/usr/local/apache2/htdocs/x': Read-only file system
httpd.pid
```

Apache runs. Writing to `htdocs` is refused: the rest of the root stays
closed. The `httpd.pid` file is in the volume. An `emptyDir` does not outlive
the Pod, and that is intended: the directory only serves the running process.

## 🔑 Exercise 3: drop every capability, then give one back

Create a busybox Pod that drops every capability (`drop: [ALL]`), and try to
change the owner of `/tmp`:

```bash
kubectl run sondeur --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-fige --overrides='{"spec":{"containers":[{"name":"c","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"securityContext":{"capabilities":{"drop":["ALL"]}}}]}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/sondeur -n essai-fige --timeout=120s; kubectl exec sondeur -n essai-fige -- chown 1234 /tmp; echo "chown : code $?"
```

```text
pod/sondeur created
pod/sondeur condition met
chown: /tmp: Operation not permitted
command terminated with exit code 1
chown : code 1
```

Refused, although the process runs as root: without the `CHOWN` capability,
root itself cannot change an owner. Recreate the Pod giving back that single
capability (`add: [CHOWN]`), and read the active capabilities:

```bash
kubectl delete pod sondeur -n essai-fige; kubectl run sondeur --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-fige --overrides='{"spec":{"containers":[{"name":"c","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"securityContext":{"capabilities":{"drop":["ALL"],"add":["CHOWN"]}}}]}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/sondeur -n essai-fige --timeout=120s; kubectl exec sondeur -n essai-fige -- chown 1234 /tmp; echo "chown : code $?"; kubectl exec sondeur -n essai-fige -- grep CapEff /proc/1/status
```

```text
pod "sondeur" deleted from essai-fige namespace
pod/sondeur created
pod/sondeur condition met
chown : code 0
CapEff:	0000000000000001
```

The `chown` goes through, and `CapEff` is 1: a single bit, the one for
`CHOWN`. Dropping everything then giving back what is missing gives a short,
readable list, instead of the runtime's default list.

## 🎛️ Exercise 4: a sysctl the kubelet refuses

A Pod can ask for kernel settings specific to its network namespace, through
`securityContext.sysctls`. Ask for `net.core.somaxconn`:

```bash
kubectl run reglage --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-fige --overrides='{"spec":{"securityContext":{"sysctls":[{"name":"net.core.somaxconn","value":"2048"}]}}}' -- sleep 3600; sleep 10; kubectl get pod reglage -n essai-fige; kubectl get pod reglage -n essai-fige -o jsonpath='{.status.reason}: {.status.message}{"\n"}'
```

```text
pod/reglage created
NAME      READY   STATUS            RESTARTS   AGE
reglage   0/1     SysctlForbidden   0          10s
SysctlForbidden: Pod was rejected: forbidden sysctl: "net.core.somaxconn" not allowlisted
```

The kubelet rejects the Pod (`SysctlForbidden`): this setting is not on the
list of those it considers safe. Now ask for
`net.ipv4.ip_unprivileged_port_start`, which is on it:

```bash
kubectl delete pod reglage -n essai-fige; kubectl run reglage --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-fige --overrides='{"spec":{"securityContext":{"sysctls":[{"name":"net.ipv4.ip_unprivileged_port_start","value":"80"}]}}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/reglage -n essai-fige --timeout=120s; kubectl exec reglage -n essai-fige -- cat /proc/sys/net/ipv4/ip_unprivileged_port_start
```

```text
pod "reglage" deleted from essai-fige namespace
pod/reglage created
pod/reglage condition met
80
```

Accepted, and the value is indeed 80 inside the Pod. This setting lets an
unprivileged process listen on port 80: it avoids keeping a capability such as
`NET_BIND_SERVICE` for a web server.

## 🧹 Clean-up

Delete the scratch namespace:

```bash
kubectl delete namespace essai-fige
```

```text
namespace "essai-fige" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cks-security-context-immutable
dsoxlab check cks-security-context-immutable
```

```text
╭─ Result: cks-security-context-immutable ─╮
│  0 / 100 pts                             │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests         │
╰──────────────────────────────────────────╯
```

0 out of 5: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a web server to lock down, which must keep
answering.

```bash
dsoxlab run cks-security-context-immutable
dsoxlab challenge cks-security-context-immutable
```
