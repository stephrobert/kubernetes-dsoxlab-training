# Read the CRI, CNI and CSI interfaces of a node

## The situation

A node that stays `NotReady`, a Pod that does not start, a volume that does not
mount: each of these failures lives behind one of the three interfaces
Kubernetes delegates to an external component. Before troubleshooting, you need
to know **where to look** on a node.

You are on **`k8s-cp.lab`**, a node of the kubeadm cluster, with `kubectl`
configured. The file **`~/interfaces/reponses.yaml`** waits for what you are
going to read.

## What you must achieve

In `~/interfaces/reponses.yaml`:

1. **`runtime_socket`**: the container runtime socket the **kubelet** uses, as
   it declares it.
2. **`runtime`**: the runtime and its version, as the node **reports them to the
   API** (`name://version`).
3. **`cni_config`** and **`cni_plugin`**: the CNI configuration file **in
   force** in `/etc/cni/net.d`, and the type of its **first plugin**.
4. **`csi_drivers`**: the exact list of **CSI drivers** registered in the
   cluster.

## Useful bearings

- The kubelet describes its configuration in `/var/lib/kubelet/config.yaml`,
  and kubeadm passes its options in `/var/lib/kubelet/kubeadm-flags.env`.
- What the node reports to the API reads in `kubectl get node -o wide` or in its
  `status.nodeInfo`.
- When several files are present in `/etc/cni/net.d`, the runtime takes the
  **first one in alphabetical order**.
- CSI drivers register as `CSIDriver` objects.

## How you will know it works

Each test reads the real value on the node at check time and compares it with
your answer. A value copied from documentation does not pass: only this
cluster's counts.

```bash
dsoxlab check k8s-lire-les-interfaces-d-un-noeud
```
