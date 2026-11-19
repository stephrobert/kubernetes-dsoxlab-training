# Challenge: Audit network flows with Hubble

## The situation

In the namespace **`magasin`** of the Cilium cluster, an API (`api`, on
`net-w1.lab`) is called every two seconds by three clients, **`vitrine`**,
**`panier`** and **`compta`**, all on `net-w2.lab`. A NetworkPolicy,
**`api-entrant`**, protects the API. Since its deployment, one of the three
clients complains that the API no longer answers, and nobody knows which one.

The security team does not want the policy lifted: it wants the refusal
**audited**. Which flow is refused and why, a metric that counts these
refusals Pod by Pod, and a log of the refusals on the node, that can be kept.

You are on the control plane `net-cp.lab`, with `kubectl` and `helm`. The
cluster runs without kube-proxy, with Cilium 1.20.5, Hubble and the Hubble
metrics enabled (port 9965 of each node). Cilium 1.20.5 declares support for
Kubernetes 1.33 to 1.36, and this cluster runs 1.37.

## What you must obtain

1. A ConfigMap **`constat`** in the namespace `magasin`, with two keys:
   **`pod-source`**, the name of the refused client Pod, and **`raison`**, the
   drop reason as Hubble names it.
2. The metric **`hubble_drop_total`** of `net-w1.lab` names the refused Pod as
   its source (`source="magasin/<pod>"`), and keeps growing: the refusal stays
   in place.
3. The refused flows are logged on the node, in
   **`/var/run/cilium/hubble/events.log`**, and this file holds **only**
   `DROPPED` flows.

## The method, step by step

**Find the right agent.** An ingress policy is enforced where the destination
Pod lives. `kubectl -n magasin get pods -o wide` shows that `api` runs on
`net-w1.lab`; `kubectl -n kube-system get pods -l k8s-app=cilium -o wide` gives
the Cilium agent of that node. Every agent embeds the `hubble` client.

**Read the refusals.** `kubectl -n kube-system exec <agent> -c cilium-agent --
hubble observe --namespace magasin --verdict DROPPED` only shows the refused
flows: source Pod, destination Pod, port, and the reason of the refusal
next to the verdict. With `-o json`, the reason is the `drop_reason_desc` field.
Hubble also keeps the flows of previous runs: `--since 1m` shows only the
current refusals, and the refused client changes at every `dsoxlab run`.
`--print-raw-filters` shows the filter that the options build, which you will
need again below. Record what you saw:

```bash
kubectl -n magasin create configmap constat \
  --from-literal=pod-source=<pod> --from-literal=raison=<reason>
```

**Read the metric.** `curl -s http://<net-w1 address>:9965/metrics | grep
hubble_drop_total` (the address: `kubectl get node net-w1.lab -o wide`). The
series carry the reason and the protocol, not the Pod: they say that something
is refused, not who. The drop metric accepts a context, written in its name in
the chart values: `drop:sourceContext=pod;destinationContext=pod` adds the
labels `source` and `destination`.

**Export the refusals.** The `hubble.export.static` values of the chart write
the flows to a file on the node: `enabled`, `filePath`
(`/var/run/cilium/hubble/events.log`) and `allowList`, a list of filters in
the format `--print-raw-filters` prints. A filter on the verdict keeps only
the refusals.

**Apply both changes.** A semicolon and commas do not survive `--set`: write a
values file that repeats the **whole** list `hubble.metrics.enabled` (a `-f`
replaces a list, it does not extend it) and adds `hubble.export.static`. Then,
after `helm repo add cilium https://helm.cilium.io` if your user does not have
the repository yet:

```bash
helm upgrade cilium cilium/cilium --version 1.20.5 --namespace kube-system \
  --reuse-values -f <your file> --wait
```

The cluster restarts the agents when their configuration changes
(`rollOutCiliumPods`): `kubectl -n kube-system rollout status ds/cilium`, then
read the metric and the file again (`sudo tail` on `net-w1.lab`, which `ssh
net-w1.lab` opens).

**Do not touch the policy.** The lab audits a refusal, it does not lift it.

## How you will know it works

The tests compare the constat with the client drawn by the setup and with the
reason Hubble gives at check time, read the metric twice twelve seconds apart
on `net-w1.lab`, then the export file of that node.

```bash
dsoxlab check k8s-auditer-les-flux-avec-hubble
```
