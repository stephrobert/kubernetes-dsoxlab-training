# Challenge: Close the API server and the kubelet to anonymous clients without breaking kubeadm join

## The situation

You are on the control plane **`k8s-cp.lab`** of a kubeadm cluster, with
`kubectl` configured and `sudo`. An audit found three doors open to clients
**without credentials**:

- an anonymous client **reads the cluster objects**: a ClusterRoleBinding
  grants a role to the group `system:unauthenticated`;
- the control plane **kubelet** answers an anonymous client on port `10250`,
  and lets it do anything;
- the API server runs **without the `NodeRestriction` admission plugin**,
  which kubeadm does enable.

One constraint: new workers will join this cluster with `kubeadm join` and a
token. That join must keep working.

## What you must achieve

1. An anonymous client only reaches the health paths (`/livez`, `/readyz`,
   `/healthz`) and what `kubeadm join` needs. Everywhere else, the API server
   answers **401**. The authentication configuration lives in
   **`/etc/kubernetes/authn-config.yaml`**.
2. No RBAC binding grants rights to anonymous clients, apart from
   `system:public-info-viewer`, which the API server sets at startup, and
   `kubeadm:bootstrap-signer-clusterinfo`, which kubeadm creates to read
   `cluster-info`.
3. The control plane kubelet answers **401** to an anonymous client, and
   **delegates** its authorization decisions to the API server.
4. The kubelet credentials can no longer set a `node-restriction.kubernetes.io/`
   label on their own node.

## Landmarks

`curl -sk` without credentials, with `-w '%{http_code}'`, tells what the API
server and the kubelet grant an anonymous client. To know what RBAC leaves it, ask as admin with a **SubjectAccessReview**
(`user: system:anonymous`, `groups: [system:unauthenticated]`): `kubectl auth
can-i --as=system:anonymous` always fails, since the anonymous user may not ask
the question itself.

`--anonymous-auth=false` closes everything, `kubeadm join` discovery included:
the join would then retry forever on a 401 error. An
**AuthenticationConfiguration** keeps anonymous access on a list of paths only.

The API server is a **static Pod**: the kubelet recreates it as soon as its
manifest changes, and an invalid manifest keeps it from coming back. Keep a
copy of the manifest **outside** `/etc/kubernetes/manifests`, which the kubelet
watches. A file the API server reads must be mounted into its Pod.

The kubelet credentials are in `/etc/kubernetes/kubelet.conf`.

## How you will know it works

The tests query the API server and the kubelet without credentials, read the
RBAC bindings of the cluster, and try to set a reserved label with the kubelet
credentials.

```bash
dsoxlab check cks-restreindre-l-acces-anonyme
```
