# Remove from a worker node what listens without serving Kubernetes

The lesson shows how to harden the nodes of a cluster. This course adds cases
the lesson does not show: tracing an open port back to its process, its
package and its systemd service, recognising a service started by hand that
would not come back after a reboot, and the difference between disabling and
masking a service.

You work on `k8s-w1.lab`, over `ssh` from the control plane. The challenge is
about another node: you will do it on your own, at the end.

Related page (in French): [Durcir les nœuds d'un cluster Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/durcir-les-noeuds/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-reduire-la-surface-du-noeud
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it, and `ssh` reaches the
workers.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

## 👂 Exercise 1: who listens, and for which package

`ss -tlnp` lists the TCP ports listening, with the process behind each one.
On `k8s-w1.lab`:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo ss -tlnpH | awk "{print \$4, \$6}" | sort -u' | head -8
```

```text
*:10250 users:(("kubelet",pid=23439,fd=26))
*:10256 users:(("kube-proxy",pid=22343,fd=11))
0.0.0.0:179 users:(("bird",pid=20160,fd=7))
0.0.0.0:22 users:(("sshd",pid=751,fd=3),("systemd",pid=1,fd=176))
127.0.0.1:10248 users:(("kubelet",pid=23439,fd=17))
127.0.0.1:10249 users:(("kube-proxy",pid=22343,fd=13))
127.0.0.1:38785 users:(("containerd",pid=62124,fd=78))
127.0.0.1:9099 users:(("calico-node",pid=19964,fd=4))
```

Each line has its explanation: the kubelet (10250, 10248), kube-proxy (10256,
10249), Calico's `bird` (179), sshd (22), containerd and calico-node locally.
A port that cannot be explained this way is suspicious. To trace a port back
to its origin, start from its process:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'P=$(sudo ss -tlnpH "sport = :22" | grep -o "pid=[0-9]*" | head -1 | cut -d= -f2); B=$(sudo readlink /proc/$P/exe); echo "pid $P -> $B"; dpkg -S $B; systemctl status $P --no-pager | head -1'
```

```text
pid 751 -> /usr/sbin/sshd
openssh-server: /usr/sbin/sshd
● ssh.service - OpenBSD Secure Shell server
```

The process on port 22 is `/usr/sbin/sshd`, provided by the `openssh-server`
package, and started by the `ssh.service` service. To remove a service for
good, you need to know which of these three levels to act on.

## 🪤 Exercise 2: a service started by hand

Start a small web server as a temporary service (`essai-ecoute` means "trial
listener"):

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo systemd-run --unit essai-ecoute python3 -m http.server 8099 >/dev/null 2>&1; sleep 2; sudo ss -tlnp "sport = :8099" | tail -1; systemctl is-enabled essai-ecoute 2>&1'
```

```text
LISTEN 0      5            0.0.0.0:8099      0.0.0.0:*    users:(("python3",pid=63228,fd=3))
transient
```

Port 8099 listens, but the service is `transient`: it was started by hand and
no file describes it. It will not come back after a reboot, and `systemctl
disable` has nothing to disable. Stopping it is enough:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo systemctl stop essai-ecoute; sudo ss -tln "sport = :8099" | tail -n +2 | wc -l'
```

```text
0
```

Nothing listens on 8099 any more.

## 🚫 Exercise 3: disable or mask

Disable the `apt-daily.timer` timer, then try to start it:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'systemctl is-enabled apt-daily.timer; sudo systemctl disable apt-daily.timer 2>&1 | tail -1; systemctl is-enabled apt-daily.timer; sudo systemctl start apt-daily.timer; systemctl is-active apt-daily.timer'
```

```text
enabled
Removed "/etc/systemd/system/timers.target.wants/apt-daily.timer".
disabled
active
```

Disabled, it no longer starts **on its own** when the node boots, but it still
starts on request. Now mask it:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo systemctl mask apt-daily.timer >/dev/null 2>&1; ls -l /etc/systemd/system/apt-daily.timer; sudo systemctl start apt-daily.timer; echo "start : code $?"; systemctl is-enabled apt-daily.timer'
```

```text
lrwxrwxrwx 1 root root 9 Nov 21 11:32 /etc/systemd/system/apt-daily.timer -> /dev/null
Failed to start apt-daily.timer: Unit apt-daily.timer is masked.
start : code 1
masked
```

Masked, it is linked to `/dev/null`: nobody can start it any more, neither the
node nor another service that would depend on it. Masking is the safe way to
keep off a service you cannot uninstall.

## 🧹 Clean-up

Unmask and enable the timer again, then check the temporary service is gone:

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo systemctl unmask apt-daily.timer >/dev/null 2>&1; sudo systemctl enable --now apt-daily.timer >/dev/null 2>&1; systemctl is-enabled apt-daily.timer; systemctl is-active essai-ecoute 2>&1'
```

```text
enabled
inactive
```

The timer is `enabled` again. `essai-ecoute` is `inactive`: once stopped, a
temporary service no longer exists.

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cks-reduire-la-surface-du-noeud
dsoxlab check cks-reduire-la-surface-du-noeud
```

```text
╭─ Result: cks-reduire-la-surface-du-noeud ─╮
│  0 / 100 pts                              │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests          │
╰───────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a worker where services that do not serve
Kubernetes are listening, to remove for good without breaking the node.

```bash
dsoxlab run cks-reduire-la-surface-du-noeud
dsoxlab challenge cks-reduire-la-surface-du-noeud
```
