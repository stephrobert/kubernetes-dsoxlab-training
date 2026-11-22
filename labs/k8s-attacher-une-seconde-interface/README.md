# Give a Pod a second interface

The lesson installs Multus next to Cilium and attaches a second macvlan
network to Pods through a NetworkAttachmentDefinition. This course looks at
what Multus does for you: it calls a **CNI plugin**, a plain executable on the
node, with a JSON configuration. You will call that plugin yourself, without
Multus and without a Pod, to see what it creates, what it answers when it
fails, and what sets macvlan apart from ipvlan.

You work in scratch network namespaces, `essai-a`, `essai-b` and `essai-c`,
on the `192.168.200.0/24` network. The challenge is about Multus, other Pods
and another network: you will do it on your own, at the end.

Related page: [Give a Pod several interfaces with Multus](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/multus-pod-interfaces/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-attacher-une-seconde-interface
```

You are now connected to `net-cp.lab`, the control plane of the Cilium
cluster. The exercises take place on the two workers, `net-w1.lab` and
`net-w2.lab`, where the `macvlan`, `ipvlan` and `static` plugins are
installed in `/opt/cni/bin`.

The outputs shown in this course were captured on these machines on
22 November 2026 (Kubernetes v1.37.2, Cilium 1.20.5, reference CNI plugins).

## 🔌 Exercise 1: call a CNI plugin by hand

A CNI plugin reads its configuration on its standard input and gets the rest
from environment variables: the action (`CNI_COMMAND`), the network namespace
to equip (`CNI_NETNS`) and the name of the interface to create
(`CNI_IFNAME`). This is exactly what Multus does for each network of a Pod. On
`net-w1.lab`, create a scratch network namespace, the configuration of a
macvlan network with a fixed address, then call the plugin with the `ADD`
action:

```bash
ssh net-w1.lab
sudo ip netns add essai-a; mkdir -p /tmp/essai-cni
cat > /tmp/essai-cni/essai-a.json <<'JSON'
{
  "cniVersion": "1.0.0",
  "name": "essai-stockage",
  "type": "macvlan",
  "master": "enp1s0",
  "mode": "bridge",
  "ipam": {"type": "static", "addresses": [{"address": "192.168.200.21/24"}]}
}
JSON
sudo CNI_COMMAND=ADD CNI_CONTAINERID=essai-a CNI_NETNS=/var/run/netns/essai-a CNI_IFNAME=net1 CNI_PATH=/opt/cni/bin /opt/cni/bin/macvlan < /tmp/essai-cni/essai-a.json
```

```text
{
    "cniVersion": "1.0.0",
    "interfaces": [
        {
            "mac": "7e:18:cf:5e:be:0b",
            "name": "net1",
            "sandbox": "/var/run/netns/essai-a"
        }
    ],
    "ips": [
        {
            "address": "192.168.200.21/24",
            "interface": 0
        }
    ]
}
```

The plugin answers in JSON: the interface it created, the network namespace
that holds it and its address. This is the answer Multus copies into the
`k8s.v1.cni.cncf.io/network-status` annotation of a Pod. Look at the new
interface, and at the node interface it relies on:

```bash
sudo ip netns exec essai-a ip -br addr show net1
sudo ip netns exec essai-a ip -br link show net1
ip -br link show enp1s0
```

```text
net1@if2         UP             192.168.200.21/24 fe80::7c18:cfff:fe5e:be0b/64
net1@if2         UP             7e:18:cf:5e:be:0b <BROADCAST,MULTICAST,UP,LOWER_UP>
enp1s0           UP             52:54:8b:d2:00:14 <BROADCAST,MULTICAST,UP,LOWER_UP>
```

`net1` carries the requested address and **a MAC address of its own**,
`7e:18:cf:5e:be:0b`, different from the one of `enp1s0`. This is how macvlan
works: each added interface shows up on the network as one more machine.

## 📡 Exercise 2: an exchange from one node to the other

Do the same on `net-w2.lab`, in the `essai-b` namespace, with the address
`192.168.200.22/24`. Leave `net-w1` (`exit`), then:

```bash
ssh net-w2.lab
sudo ip netns add essai-b; mkdir -p /tmp/essai-cni
cat > /tmp/essai-cni/essai-b.json <<'JSON'
{
  "cniVersion": "1.0.0",
  "name": "essai-stockage",
  "type": "macvlan",
  "master": "enp1s0",
  "mode": "bridge",
  "ipam": {"type": "static", "addresses": [{"address": "192.168.200.22/24"}]}
}
JSON
sudo CNI_COMMAND=ADD CNI_CONTAINERID=essai-b CNI_NETNS=/var/run/netns/essai-b CNI_IFNAME=net1 CNI_PATH=/opt/cni/bin /opt/cni/bin/macvlan < /tmp/essai-cni/essai-b.json | grep -E '"(mac|address)"'
exit
```

```text
            "mac": "9e:1e:12:ed:3a:ef",
            "address": "192.168.200.22/24",
```

Back on `net-cp`, ping `essai-b`, on `net-w2`, from `essai-a`, on `net-w1`:

```bash
ssh net-w1.lab 'sudo ip netns exec essai-a ping -c 3 192.168.200.22'
```

```text
PING 192.168.200.22 (192.168.200.22) 56(84) bytes of data.
64 bytes from 192.168.200.22: icmp_seq=1 ttl=64 time=0.359 ms
64 bytes from 192.168.200.22: icmp_seq=2 ttl=64 time=0.399 ms
64 bytes from 192.168.200.22: icmp_seq=3 ttl=64 time=0.636 ms

--- 192.168.200.22 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2037ms
rtt min/avg/max/mdev = 0.359/0.464/0.636/0.122 ms
```

The two interfaces reach each other directly, in less than a millisecond,
without going through Cilium or a Service: the packet leaves through `enp1s0`
like the packet of any machine of the `10.10.50.0/24` network. `ttl=64`
confirms it: no router stood between the two.

## 🚫 Exercise 3: the answer of a plugin that fails

When a Pod stays in `ContainerCreating` behind Multus, the error often comes
from the plugin. Trigger one: call macvlan with a master interface that does
not exist, `enp9s0`. On `net-w1`, in a throwaway namespace:

```bash
ssh net-w1.lab
sudo ip netns add essai-x
sed -e 's/enp1s0/enp9s0/' -e 's/200.21/200.29/' /tmp/essai-cni/essai-a.json > /tmp/essai-cni/essai-x.json
sudo CNI_COMMAND=ADD CNI_CONTAINERID=essai-x CNI_NETNS=/var/run/netns/essai-x CNI_IFNAME=net1 CNI_PATH=/opt/cni/bin /opt/cni/bin/macvlan < /tmp/essai-cni/essai-x.json; echo "code=$?"
sudo ip netns del essai-x
```

```text
{
    "code": 999,
    "msg": "Link not found"
}code=1
```

The plugin exits with 1 and returns a JSON error with a short message: `Link
not found`. It does not name the faulty interface. Behind Multus, this is the
message that shows up in the Pod events (`kubectl describe pod`): when you
read it, compare the `master` field of the NetworkAttachmentDefinition with
`ip -br link` on the node that runs the Pod.

## 🧱 Exercise 4: macvlan and ipvlan on the same interface

ipvlan is the other way to share a node interface. Try to add one on
`enp1s0`, in a new `essai-c` namespace, while `essai-a` already has its
macvlan there. The configuration changes type, and the mode is `l2`:

```bash
sudo ip netns add essai-c
sed -e 's/"macvlan"/"ipvlan"/' -e 's/"bridge"/"l2"/' -e 's/200.21/200.23/' /tmp/essai-cni/essai-a.json > /tmp/essai-cni/essai-c.json
sudo CNI_COMMAND=ADD CNI_CONTAINERID=essai-c CNI_NETNS=/var/run/netns/essai-c CNI_IFNAME=net1 CNI_PATH=/opt/cni/bin /opt/cni/bin/ipvlan < /tmp/essai-cni/essai-c.json; echo "code=$?"
```

```text
{
    "code": 999,
    "msg": "failed to create ipvlan: device or resource busy"
}code=1
```

`device or resource busy`: the kernel refuses. An interface that already
carries a macvlan cannot carry an ipvlan, and the other way round. On a
cluster, two NetworkAttachmentDefinitions, one macvlan and one ipvlan, on the
same `master` give this error to the first Pod that asks for the second one.

## 🔁 Exercise 5: give the interface back, then compare with ipvlan

The `DEL` action is the one the plugin receives when a Pod is deleted. Give
back the interface of `essai-a` with the same configuration, then run the
ipvlan again:

```bash
sudo CNI_COMMAND=DEL CNI_CONTAINERID=essai-a CNI_NETNS=/var/run/netns/essai-a CNI_IFNAME=net1 CNI_PATH=/opt/cni/bin /opt/cni/bin/macvlan < /tmp/essai-cni/essai-a.json; echo "code=$?"
sudo ip netns exec essai-a ip -br link
sudo CNI_COMMAND=ADD CNI_CONTAINERID=essai-c CNI_NETNS=/var/run/netns/essai-c CNI_IFNAME=net1 CNI_PATH=/opt/cni/bin /opt/cni/bin/ipvlan < /tmp/essai-cni/essai-c.json > /dev/null; echo "code=$?"
sudo ip netns exec essai-c ip -br link show net1
ip -br link show enp1s0
```

```text
code=0
lo               DOWN           00:00:00:00:00:00 <LOOPBACK>
code=0
net1@if2         UNKNOWN        52:54:8b:d2:00:14 <BROADCAST,MULTICAST,UP,LOWER_UP>
enp1s0           UP             52:54:8b:d2:00:14 <BROADCAST,MULTICAST,UP,LOWER_UP>
```

After `DEL`, only the `lo` interface is left in `essai-a`: `net1` is gone,
and the ipvlan goes through. Its `net1` carries **the same MAC** as `enp1s0`.
Check what `net-w2` sees after a ping:

```bash
sudo ip netns exec essai-c ping -c 2 192.168.200.22 | tail -2
exit
ssh net-w2.lab 'sudo ip netns exec essai-b ip neigh show 192.168.200.23; sudo ip netns exec essai-b ip neigh show 192.168.200.21'
```

```text
2 packets transmitted, 2 received, 0% packet loss, time 1023ms
rtt min/avg/max/mdev = 0.341/0.446/0.552/0.105 ms
192.168.200.23 dev net1 lladdr 52:54:8b:d2:00:14 DELAY
192.168.200.21 dev net1 lladdr 7e:18:cf:5e:be:0b DELAY
```

For `essai-b`, the ipvlan address `.23` has the MAC of the `net-w1` card,
while the macvlan address `.21` had its own. This is the difference that
drives the choice: on a network that limits the number of MAC addresses per
port (a filtered switch, a cloud network), macvlan fails where ipvlan works.

## 🧹 Clean-up

Give back the two interfaces still attached, then delete the scratch
namespaces and the configuration files, on each worker:

```bash
ssh net-w1.lab 'sudo CNI_COMMAND=DEL CNI_CONTAINERID=essai-c CNI_NETNS=/var/run/netns/essai-c CNI_IFNAME=net1 CNI_PATH=/opt/cni/bin /opt/cni/bin/ipvlan < /tmp/essai-cni/essai-c.json; sudo ip netns del essai-a; sudo ip netns del essai-c; rm -rf /tmp/essai-cni'
ssh net-w2.lab 'sudo CNI_COMMAND=DEL CNI_CONTAINERID=essai-b CNI_NETNS=/var/run/netns/essai-b CNI_IFNAME=net1 CNI_PATH=/opt/cni/bin /opt/cni/bin/macvlan < /tmp/essai-cni/essai-b.json; sudo ip netns del essai-b; rm -rf /tmp/essai-cni'
for n in net-w1.lab net-w2.lab; do ssh $n 'ip netns list | grep -c essai'; done
```

```text
0
0
```

No scratch namespace is left on the two workers. Then leave the machine and
reset the lab. `dsoxlab reset` replays the clean-up and then the lab
preparation: you get back exactly the starting state of the challenge. It
asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-attacher-une-seconde-interface
dsoxlab check k8s-attacher-une-seconde-interface
```

```text
╭─ Result: k8s-attacher-une-seconde-interface ─╮
│  0 / 100 pts                                 │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests             │
╰──────────────────────────────────────────────╯
```

0 out of 5: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: let Cilium share the CNI configuration,
install Multus, and give two Pods a second interface on a storage network,
from one node to the other.

```bash
dsoxlab run k8s-attacher-une-seconde-interface
dsoxlab challenge k8s-attacher-une-seconde-interface
```
