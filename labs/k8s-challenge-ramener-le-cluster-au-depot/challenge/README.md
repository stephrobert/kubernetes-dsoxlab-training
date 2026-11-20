# Challenge: Bring live changes back to the Git repository

## 📍 The situation

The company directory runs on the kubeadm cluster, in the **`annuaire`**
namespace. Its manifests live in the git repository **`~/annuaire`**, which is
the source of truth: the `annuaire-config` ConfigMap, the `annuaire-api`
Deployment and its Service. You are on the control plane, with `kubectl`
configured.

Last night, during an incident, the on-call engineer changed the directory
**live on the cluster**, without going through the repository. Nobody wrote
down what. The team decided this morning: it **keeps the replica count**
raised during the incident, and **nothing else**.

## 🎯 What you must obtain

1. `kubectl diff` run against the `~/annuaire` repository finds **no gap**
   with the cluster. **Blocking requirement.**
2. The replica count raised during the night is **kept in the cluster** and
   **carried into the repository**, in a commit. The working tree of the
   repository is clean. **Blocking requirement.**
3. All the **other** live changes are gone.
4. The Deployment and the ConfigMap are the **original objects**: changed,
   never deleted or recreated.
5. Every replica of the directory runs on the **configuration of the
   repository**.

## 🧭 Useful landmarks

A live change does not always show in `kubectl diff`.

## ✅ How you will know it works

The tests read the cluster and the git repository, run `kubectl diff` against
the repository again, and read the configuration of each Pod. The replica
count and the changed values are drawn at random during the preparation. The
pass mark is 80%, and both blocking requirements must be met.

```bash
dsoxlab check k8s-challenge-ramener-le-cluster-au-depot
```
