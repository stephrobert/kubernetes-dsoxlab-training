# Repair a kubelet that refuses to start

The lesson shows how to troubleshoot a kubelet that no longer starts. In this
lab, the worker's kubelet is down: that is the challenge. This course works
on the control plane's kubelet, and adds cases the lesson does not show: the
three sources of its configuration, the configuration it really applies,
read through the API, a setting changed then restored, and its log filtered
by priority.

Related page: [Troubleshoot a node](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/troubleshoot-a-node/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-troubleshoot-kubelet
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it. The kubelet's files
belong to root: the commands use `sudo`.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

## 📂 Exercise 1: where the kubelet gets its configuration from

The kubelet's systemd service is made of several files. Display them, keeping
only the useful lines:

```bash
systemctl cat kubelet | grep -E '^# /|ExecStart=/|EnvironmentFile' | head -6
```

```text
# /usr/lib/systemd/system/kubelet.service
ExecStart=/usr/bin/kubelet
# /usr/lib/systemd/system/kubelet.service.d/10-kubeadm.conf
EnvironmentFile=-/var/lib/kubelet/kubeadm-flags.env
EnvironmentFile=-/etc/default/kubelet
ExecStart=/usr/bin/kubelet $KUBELET_KUBECONFIG_ARGS $KUBELET_CONFIG_ARGS $KUBELET_KUBEADM_ARGS $KUBELET_EXTRA_ARGS
```

The base service, completed by `10-kubeadm.conf`, which adds two variable
files and the real start line. Read the first variable file, then a few
settings of the kubelet's configuration file:

```bash
sudo cat /var/lib/kubelet/kubeadm-flags.env; sudo grep -E '^(clusterDNS|clusterDomain|maxPods|cgroupDriver)' -A1 /var/lib/kubelet/config.yaml | head -6
```

```text
KUBELET_KUBEADM_ARGS=""
cgroupDriver: systemd
clusterDNS:
- 10.96.0.10
clusterDomain: cluster.local
containerRuntimeEndpoint: unix:///var/run/containerd/containerd.sock
```

Three sources then: the service's start line, the variables
(`kubeadm-flags.env`, empty here), and the `/var/lib/kubelet/config.yaml`
file. A startup failure can come from any of them: you must read all three.

## 🔎 Exercise 2: the live configuration, read through the API

The kubelet publishes the configuration it applies, and the API server can
relay it (`/proxy/configz`):

```bash
kubectl get --raw /api/v1/nodes/k8s-cp.lab/proxy/configz | python3 -c 'import json,sys; c=json.load(sys.stdin)["kubeletconfig"]; print("maxPods", c["maxPods"], "| clusterDNS", c["clusterDNS"], "| staticPodPath", c["staticPodPath"])'
```

```text
maxPods 110 | clusterDNS ['10.96.0.10'] | staticPodPath /etc/kubernetes/manifests
```

This is the configuration in service, not the file's. The two differ when the
file was changed without restarting the kubelet, or when a start-line option
takes precedence.

## 🎚️ Exercise 3: change a setting, then restore it

Back up the configuration file, and read how many Pods the node accepts
(`pods allouables` means "allocatable pods"):

```bash
sudo cp /var/lib/kubelet/config.yaml ~/kubelet-config.sauve.yaml; kubectl get node k8s-cp.lab -o jsonpath='pods allouables={.status.allocatable.pods}{"\n"}'
```

```text
pods allouables=110
```

Set `maxPods` to 42, restart the kubelet, and read again:

```bash
sudo grep -q '^maxPods:' /var/lib/kubelet/config.yaml && sudo sed -i 's/^maxPods:.*/maxPods: 42/' /var/lib/kubelet/config.yaml || echo 'maxPods: 42' | sudo tee -a /var/lib/kubelet/config.yaml >/dev/null; sudo systemctl restart kubelet; sleep 15; kubectl get node k8s-cp.lab -o jsonpath='pods allouables={.status.allocatable.pods}{"\n"}'
```

```text
pods allouables=42
```

The node now only accepts 42 Pods: the kubelet reread its file on restart,
and announced it to the API. Put the backup back:

```bash
sudo cp ~/kubelet-config.sauve.yaml /var/lib/kubelet/config.yaml; sudo systemctl restart kubelet; sleep 15; kubectl get node k8s-cp.lab -o jsonpath='pods allouables={.status.allocatable.pods}{"\n"}'
```

```text
pods allouables=110
```

Back to 110, the default value. Backing up the file before touching it lets
you roll back in one command if the kubelet does not restart.

## 📜 Exercise 4: the log, filtered by priority

The kubelet's log is chatty. `-p err` only keeps errors. Look for some in the
last two minutes, which include two restarts (the last line reads "error
lines of the last two minutes"):

```bash
sudo journalctl -u kubelet --since '-2 min' -p err --no-pager | tail -3 | cut -c1-200; echo "(lignes d'erreur des deux dernières minutes)"
```

```text
-- No entries --
(lignes d'erreur des deux dernières minutes)
```

No error: both restarts went fine. On a kubelet that refuses to start, this
filter is what brings out the line that matters. Finally, check its health
endpoint (`santé du kubelet` means "kubelet health"):

```bash
printf 'santé du kubelet : '; curl -s "http://127.0.0.1:10248/healthz"; echo
```

```text
santé du kubelet : ok
```

## 🧹 Clean-up

Delete the backup and check the kubelet runs:

```bash
sudo rm -f ~/kubelet-config.sauve.yaml; systemctl is-active kubelet
```

```text
active
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-troubleshoot-kubelet
dsoxlab check cka-troubleshoot-kubelet
```

```text
╭─ Result: cka-troubleshoot-kubelet ─╮
│  0 / 100 pts                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests   │
╰────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: the worker's kubelet refuses to start, and
it must come back with a valid configuration.

```bash
dsoxlab run cka-troubleshoot-kubelet
dsoxlab challenge cka-troubleshoot-kubelet
```
