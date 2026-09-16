# Require mTLS in a mesh, and prove it with a client left outside

**CKS** lab, *Monitoring, Logging and Runtime Security* domain (20 % of the
exam), Pod-to-Pod traffic encryption.

The lab does not teach how to install a mesh: the setup puts one in place.
What it measures is the **requirement**, and the fact that it acts. A mesh
installed without a PeerAuthentication runs in PERMISSIVE mode: it accepts
encrypted and plain traffic alike, and protects nothing. That is the gap this
lab makes visible.

The proof hangs on no string of characters: the test waits for the Pod without
a sidecar to be blocked, then checks that the meshed Pod still gets through.
Both measurements live in the **same** test, deliberately. "The meshed client
gets through" is already true BEFORE the work: on its own, that assertion
would make a green test measuring nothing.

Measured on 2026-09-16, on this setup:

- istiod in the `minimal` profile consumes about **194 MB**, well within the
  control plane's 4 GB. The default profile adds gateways this lab has no use
  for;
- without a PeerAuthentication, `client-nu` gets the page; with STRICT, its
  connection is refused by the service's sidecar, while `client-maille` is
  still served.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 30 minutes |
| Companion lesson | [Encrypting Pod-to-Pod traffic with mTLS](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/mtls-pod-to-pod/) |

```bash
dsoxlab run   cks-istio-mtls-lockdown
dsoxlab check cks-istio-mtls-lockdown
```

The `cleanup.yaml` uninstalls Istio entirely with `istioctl uninstall
--purge`. CRDs and webhooks are **cluster-scoped** objects: they would outlive
the namespaces, and the validator would count them as a trace left for the
next lab.

**Yet the purge is not enough**, and the validator is what found it: istiod
pushes its root CA certificate into an `istio-ca-root-cert` ConfigMap in
**every** namespace, `kube-system` included, and `--purge` leaves those copies
behind. Since each installation generates a new CA, the ConfigMap is not only
left behind, its content **changes** from one run to the next. The first run
went RED on exactly that:

```
kube-system configmap/istio-ca-root-cert: 'f6df77835939' became '0d2005cac2d8'
```

So the cleanup enumerates the namespaces to remove them one by one, `kubectl
delete` not accepting `--all-namespaces`.

Written on 2026-09-16, then validated by `scripts/valider-labs.py`: 0 before
the work, 100 after the trainer's solution, replayable and leaving no trace.
