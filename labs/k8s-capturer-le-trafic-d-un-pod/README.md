# Capture the traffic of a Pod

The lesson shows three ways to capture a Pod's traffic (the node's `cali`
interface, `nsenter`, `kubectl debug`) and how to recognise a refusal, a loss
or a DNS failure. This course adds what it mentions without showing: finding
the node interface from inside the Pod, capturing on the server side to see
who really sends an RST, measuring the delays between packets, counting the
DNS queries of a short name, and capturing without adding anything to the
original Pod.

You work in the `essai-capture` namespace, with an `echo` server and a
`sonde` probe that calls a badly configured Service. The challenge uses other
Pods and other failures, drawn at random: you will do it on your own, at the
end.

Related page: [Capture the traffic of a Pod](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/reseau-avance/capturer-trafic-pod/) (in French).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-capturer-le-trafic-d-un-pod
```

You are now connected to `k8s-cp.lab`, the control plane of the kubeadm
cluster, which has two workers, `k8s-w1.lab` and `k8s-w2.lab`. Create the
scratch objects: the `echo` server on `k8s-w1`, listening on port 5678, an
`echo-ferme` Service whose target port is 5690, where nothing listens, and the
probe on `k8s-w2`, which calls that Service every 2 seconds.

```bash
kubectl create namespace essai-capture; cat <<'YAML' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: echo
  namespace: essai-capture
  labels:
    app: echo
spec:
  nodeName: k8s-w1.lab
  containers:
    - name: echo
      image: hashicorp/http-echo:1.0.0
      args: ["-text=essai", "-listen=:5678"]
---
apiVersion: v1
kind: Service
metadata:
  name: echo-ferme
  namespace: essai-capture
spec:
  selector:
    app: echo
  ports:
    - port: 80
      targetPort: 5690
---
apiVersion: v1
kind: Pod
metadata:
  name: sonde
  namespace: essai-capture
spec:
  nodeName: k8s-w2.lab
  containers:
    - name: curl
      image: curlimages/curl:8.22.0
      command: ["sh", "-c", "while true; do curl -sS -m 3 'http://echo-ferme/'; sleep 2; done"]
YAML
kubectl -n essai-capture wait --for=condition=Ready pod/echo pod/sonde --timeout=120s
kubectl -n essai-capture get pods -o wide; kubectl -n essai-capture get svc echo-ferme
```

```text
NAME    READY   STATUS    RESTARTS   AGE   IP              NODE         NOMINATED NODE   READINESS GATES
echo    1/1     Running   0          1s    10.244.38.94    k8s-w1.lab   <none>           <none>
sonde   1/1     Running   0          1s    10.244.223.33   k8s-w2.lab   <none>           <none>
NAME         TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
echo-ferme   ClusterIP   10.98.139.126   <none>        80/TCP    1s
```

Note the two Pod addresses and the ClusterIP: yours will be different,
replace them in the commands that follow. The outputs shown in this course
were captured on these machines on 22 November 2026 (Kubernetes v1.37.2,
tcpdump 4.99.4).

## 🔗 Exercise 1: from inside the Pod to the node interface

Inside the Pod, the interface is called `eth0@ifN`, where `N` is the index of
the other end of the veth pair, on the node. That index is enough to find the
`cali` interface without knowing the Pod address. On `k8s-w2.lab`, enter the
probe's network namespace, read the index, then look for the interface that
carries it:

```bash
ssh k8s-w2.lab
id=$(sudo crictl ps --name curl -q --label io.kubernetes.pod.name=sonde | head -1)
pid=$(sudo crictl inspect --output go-template --template '{{.info.pid}}' "$id")
sudo nsenter -t "$pid" -n ip -br link show eth0
```

```text
eth0@if12        UP             c6:89:13:58:81:ce <BROADCAST,MULTICAST,UP,LOWER_UP>
```

The index is 12. Look for it among the node's interfaces, and compare with
what the route to the probe's address gives:

```bash
ip -o link | awk -F': ' '$1==12 {print $2}'
ip route get 10.244.223.33 | grep -o 'dev [^ ]*'
```

```text
cali84f4a66edb5@if2
dev cali84f4a66edb5
```

Both paths lead to the same interface. The `@if2` on the node side points
back to the index of `eth0` inside the Pod: each end of the pair names the
other. This method also works for a Pod whose container you know but not its
address.

## 🎯 Exercise 2: who really sends the RST

The lesson notes that a capture on the client side never shows the real
sender of an RST. Capture both sides at the same time: the probe on `k8s-w2`,
the server on `k8s-w1`. Leave `k8s-w2` (`exit`), then, from `k8s-cp`, start
the server capture in the background and the probe capture right after:

```bash
ssh k8s-w1.lab 'dev=$(ip route get 10.244.38.94 | grep -o "dev [^ ]*" | cut -d" " -f2); mkdir -p /tmp/essai-captures; sudo timeout 7 tcpdump -i $dev -nn -U -w /tmp/essai-captures/echo.pcap tcp' &
ssh k8s-w2.lab 'dev=$(ip route get 10.244.223.33 | grep -o "dev [^ ]*" | cut -d" " -f2); mkdir -p /tmp/essai-captures; sudo timeout 7 tcpdump -i $dev -nn -U -w /tmp/essai-captures/sonde.pcap tcp'; wait
ssh k8s-w2.lab 'sudo tcpdump -nn -r /tmp/essai-captures/sonde.pcap 2>/dev/null | head -2'
ssh k8s-w1.lab 'sudo tcpdump -nn -r /tmp/essai-captures/echo.pcap 2>/dev/null | head -2'
```

```text
21:22:42.082472 IP 10.244.223.33.45806 > 10.98.139.126.80: Flags [S], seq 1204700480, win 64860, options [mss 1410,sackOK,TS val 2435128213 ecr 0,nop,wscale 7], length 0
21:22:42.082551 IP 10.98.139.126.80 > 10.244.223.33.45806: Flags [R.], seq 0, ack 1204700481, win 0, length 0
21:22:42.082057 IP 10.244.223.33.45806 > 10.244.38.94.5690: Flags [S], seq 1204700480, win 64860, options [mss 1410,sackOK,TS val 2435128213 ecr 0,nop,wscale 7], length 0
21:22:42.082068 IP 10.244.38.94.5690 > 10.244.223.33.45806: Flags [R.], seq 0, ack 1204700481, win 0, length 0
```

The first two lines come from the probe, the last two from the server. The
`SYN` carries the same sequence number (`1204700480`) on both sides: it is the
same packet. On the probe side, the RST seems to come from the Service,
`10.98.139.126.80`. On the server side, it leaves the `echo` Pod itself,
`10.244.38.94`, on port **5690**: the Pod's kernel refuses, because nothing
listens on that port. The Service did its job by translating the address. The
clocks of the two nodes differ by a few tenths of a millisecond: compare the
sequence numbers, not the times.

## ⏱️ Exercise 3: measure the delays, and filter when reading

The lesson says a refusal is fast and a loss shows as repeated sends.
`tcpdump -ttt` shows, instead of the time of day, the time elapsed since the
previous packet: the measure is read without any calculation. Read the two
files of exercise 2 again:

```bash
ssh k8s-w2.lab 'sudo tcpdump -nn -ttt -r /tmp/essai-captures/sonde.pcap 2>/dev/null | head -4'
ssh k8s-w1.lab 'sudo tcpdump -nn -ttt -r /tmp/essai-captures/echo.pcap 2>/dev/null | head -2'
```

```text
 00:00:00.000000 IP 10.244.223.33.45806 > 10.98.139.126.80: Flags [S], seq 1204700480, win 64860, options [mss 1410,sackOK,TS val 2435128213 ecr 0,nop,wscale 7], length 0
 00:00:00.000079 IP 10.98.139.126.80 > 10.244.223.33.45806: Flags [R.], seq 0, ack 1204700481, win 0, length 0
 00:00:02.004781 IP 10.244.223.33.45812 > 10.98.139.126.80: Flags [S], seq 143838984, win 64860, options [mss 1410,sackOK,TS val 2435130218 ecr 0,nop,wscale 7], length 0
 00:00:00.000179 IP 10.98.139.126.80 > 10.244.223.33.45812: Flags [R.], seq 0, ack 143838985, win 0, length 0
 00:00:00.000000 IP 10.244.223.33.45806 > 10.244.38.94.5690: Flags [S], seq 1204700480, win 64860, options [mss 1410,sackOK,TS val 2435128213 ecr 0,nop,wscale 7], length 0
 00:00:00.000011 IP 10.244.38.94.5690 > 10.244.223.33.45806: Flags [R.], seq 0, ack 1204700481, win 0, length 0
```

The RST comes back in 79 µs on the probe side, and the server sends it in
11 µs: the difference is the trip between the two nodes. The new `SYN` leaves
2.004 s later, with another source port (`45812`) and another sequence: it is
a **new call** from the probe's loop, not a retransmission. A retransmission
keeps the same port and the same sequence.

A filter can also be applied when reading: the capture keeps everything, and
you only look at what interests you. Count the RSTs in the probe capture:

```bash
ssh k8s-w2.lab "sudo tcpdump -nn -r /tmp/essai-captures/sonde.pcap 'tcp[tcpflags] & tcp-rst != 0' 2>/dev/null | wc -l"
```

```text
3
```

Three RSTs in 7 seconds, one per call of the probe.

## 🔤 Exercise 4: what a short name costs

A Pod tries every search domain of its `/etc/resolv.conf` before the name
itself. A name that ends with a dot is already complete: no domain is added
to it. Capture the probe's DNS traffic while it looks up a name that does not
exist, first short, then complete with a final dot. Replace `cali84f4a66edb5`
with the interface found in exercise 1:

```bash
ssh k8s-w2.lab 'sudo mkdir -p /tmp/essai-captures; sudo timeout 12 tcpdump -i cali84f4a66edb5 -nn -U -w /tmp/essai-captures/dns-court.pcap udp port 53' &
sleep 2; time kubectl -n essai-capture exec sonde -- curl -sS -m 8 'http://inconnu-essai/'; wait
ssh k8s-w2.lab "sudo tcpdump -nn -r /tmp/essai-captures/dns-court.pcap 2>/dev/null | grep 'A? inconnu' | cut -d' ' -f3-"
```

```text
curl: (6) Could not resolve host: inconnu-essai
command terminated with exit code 6

real	0m5.077s
user	0m0.029s
sys	0m0.013s
10.244.223.33.32952 > 10.96.0.10.53: 10690+ A? inconnu-essai.essai-capture.svc.cluster.local. (63)
10.244.223.33.34159 > 10.96.0.10.53: 15310+ AAAA? inconnu-essai.essai-capture.svc.cluster.local. (63)
10.244.223.33.38577 > 10.96.0.10.53: 6114+ A? inconnu-essai.svc.cluster.local. (49)
10.244.223.33.46852 > 10.96.0.10.53: 43755+ AAAA? inconnu-essai.svc.cluster.local. (49)
10.244.223.33.51030 > 10.96.0.10.53: 13124+ A? inconnu-essai.cluster.local. (45)
10.244.223.33.42744 > 10.96.0.10.53: 27261+ AAAA? inconnu-essai.cluster.local. (45)
10.244.223.33.34637 > 10.96.0.10.53: 36231+ A? inconnu-essai.lab. (35)
10.244.223.33.50576 > 10.96.0.10.53: 38082+ AAAA? inconnu-essai.lab. (35)
10.244.223.33.46638 > 10.96.0.10.53: 14922+ AAAA? inconnu-essai. (31)
10.244.223.33.45192 > 10.96.0.10.53: 13381+ A? inconnu-essai. (31)
10.244.223.33.45192 > 10.96.0.10.53: 13381+ A? inconnu-essai. (31)
10.244.223.33.46638 > 10.96.0.10.53: 14922+ AAAA? inconnu-essai. (31)
```

Twelve queries for a single name: an A question (IPv4) and an AAAA question
(IPv6) for each of the four search domains, then the bare name, sent twice
with the same identifier. Those last two sends, unanswered, bring the command
to 5 seconds. Run the measure again with the complete name:

```bash
ssh k8s-w2.lab 'sudo timeout 12 tcpdump -i cali84f4a66edb5 -nn -U -w /tmp/essai-captures/dns-complet.pcap udp port 53' &
sleep 2; time kubectl -n essai-capture exec sonde -- curl -sS -m 8 'http://inconnu-essai.essai-capture.svc.cluster.local./'; wait
ssh k8s-w2.lab "sudo tcpdump -nn -r /tmp/essai-captures/dns-complet.pcap 2>/dev/null | grep 'A? inconnu' | cut -d' ' -f3-"
```

```text
curl: (6) Could not resolve host: inconnu-essai.essai-capture.svc.cluster.local.
command terminated with exit code 6

real	0m0.083s
user	0m0.032s
sys	0m0.011s
10.244.223.33.33678 > 10.96.0.10.53: 4738+ A? inconnu-essai.essai-capture.svc.cluster.local. (63)
10.244.223.33.39992 > 10.96.0.10.53: 18829+ AAAA? inconnu-essai.essai-capture.svc.cluster.local. (63)
```

Two queries, and the whole command, `kubectl exec` included, returns in
0.08 s. The error message is the same: only the capture shows the difference.
When an application takes several seconds to fail on a name, count its
queries before suspecting the DNS server.

## 🪞 Exercise 5: capture in a copy of the Pod

The lesson warns that an ephemeral container stays recorded in the Pod.
`kubectl debug --copy-to` instead creates a **copy** of the Pod, to which it
adds a capture container. The original is not touched:

```bash
kubectl -n essai-capture debug sonde --copy-to=sonde-copie \
  --image=nicolaka/netshoot:v0.16@sha256:b09d9b21381f47a79b3cbcb30da25266dc17186ea00ae65e99fdc51396f48e70 \
  --container=capture -- tcpdump -i eth0 -nn -c 4 "tcp port 80"
sleep 30; kubectl -n essai-capture get pods -o wide
kubectl -n essai-capture logs sonde-copie -c capture | cut -c1-110
```

```text
NAME          READY   STATUS     RESTARTS     AGE     IP              NODE         NOMINATED NODE   READINESS GATES
echo          1/1     Running    0            2m16s   10.244.38.94    k8s-w1.lab   <none>           <none>
sonde         1/1     Running    0            2m16s   10.244.223.33   k8s-w2.lab   <none>           <none>
sonde-copie   1/2     NotReady   1 (8s ago)   35s     10.244.223.34   k8s-w2.lab   <none>           <none>
tcpdump: verbose output suppressed, use -v[v]... for full protocol decode
listening on eth0, link-type EN10MB (Ethernet), snapshot length 262144 bytes
21:24:25.485615 IP 10.244.223.34.55756 > 10.98.139.126.80: Flags [S], seq 2662910559, win 64860, options [mss
21:24:25.486074 IP 10.98.139.126.80 > 10.244.223.34.55756: Flags [R.], seq 0, ack 2662910560, win 0, length 0
21:24:27.491714 IP 10.244.223.34.55758 > 10.98.139.126.80: Flags [S], seq 3492833395, win 64860, options [mss
21:24:27.491836 IP 10.98.139.126.80 > 10.244.223.34.55758: Flags [R.], seq 0, ack 3492833396, win 0, length 0
4 packets captured
4 packets received by filter
0 packets dropped by kernel
```

The copy replays the probe's command, so it hits the same refusal. Then
compare the containers of the two Pods:

```bash
for p in sonde sonde-copie; do printf '%-12s containers=%s ephemeral=%s\n' $p "$(kubectl -n essai-capture get pod $p -o jsonpath='{.spec.containers[*].name}')" "$(kubectl -n essai-capture get pod $p -o jsonpath='{.spec.ephemeralContainers[*].name}')"; done
```

```text
sonde        containers=curl ephemeral=
sonde-copie  containers=curl capture ephemeral=
```

The original has neither an added container nor an ephemeral one. The copy
carries a second ordinary container, `capture`. Two limits show in the
output: the copy has **its own address** (`10.244.223.34`), so you capture
its traffic, not the original's. And its `capture` container restarts every
time `tcpdump` ends (`RESTARTS 1`, `1/2`), because the copy keeps the restart
policy of the original Pod. Delete it as soon as the capture is read. This
method fits a failure that happens again at every start, not a state that
only the original reached.

## 🧹 Clean-up

Delete the scratch namespace, which takes the copy with it, then the captures
left on the two workers:

```bash
kubectl delete namespace essai-capture --wait=true --timeout=120s
for n in k8s-w1.lab k8s-w2.lab; do ssh $n sudo rm -rf /tmp/essai-captures; done
```

```text
namespace "essai-capture" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the
clean-up and then the lab preparation: you get back exactly the starting state
of the challenge, with new failures drawn at random. It asks you to confirm:
answer `y`.

```bash
exit
dsoxlab reset k8s-capturer-le-trafic-d-un-pod
dsoxlab check k8s-capturer-le-trafic-d-un-pod
```

```text
╭─ Result: k8s-capturer-le-trafic-d-un-pod ─╮
│  0 / 100 pts                              │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests          │
╰───────────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: three clients of a shop fail, each for a
different reason. Capture their traffic and name the cause of each failure,
without repairing anything.

```bash
dsoxlab run k8s-capturer-le-trafic-d-un-pod
dsoxlab challenge k8s-capturer-le-trafic-d-un-pod
```
