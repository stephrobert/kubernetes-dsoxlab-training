# Find and remove what an attacker left behind

## The situation

Last week, an attacker got into the **`facturation`** namespace of the kubeadm
cluster through a debugging Pod, **`outil-debug`**. The team revoked the token
it used, and believed the incident closed. Yet the account it ran under,
**`support-n2`**, keeps reading the Secrets of every namespace: whatever is
removed by hand comes back a minute later.

The attacker left more than an access: something in the namespace **recreates
it**. Next to it runs the **legitimate application** `facturation`: two
replicas behind a Service, its own identity `facturation`, its binding
`facturation-lecture`, and a nightly CronJob `purge-factures`. None of it may
be harmed.

You are on the control plane, with `kubectl` configured, as root.

## What you must achieve

1. The object that recreates the access is **recorded** in
   **`/root/constat-persistance.yaml`**, exported from the live object, **before
   any deletion**.
2. That object is **deleted**, along with what it already launched.
3. The **attacker's identities** and their **cluster-wide bindings** are gone:
   `support-n2` can no longer read the Secrets of the cluster.
4. The original Pod **`outil-debug`** is deleted, and the access **does not
   come back** after the next minute of scheduling.
5. The **legitimate application** is intact: replicas, identity, binding, its
   own CronJob, and it answers on its Service.

## The method, step by step

**List what runs on a schedule.** A persistence must survive the attacker's
departure, so it re-runs on its own: `kubectl get cronjobs,daemonsets,jobs -n
facturation`, then the same across the cluster with `-A`. A harmless name
proves nothing: read what each one runs (`kubectl get cronjob <name> -o yaml`,
the `command` and the `serviceAccountName`).

An admission webhook is another place to hide: it sees every object created.
`kubectl get mutatingwebhookconfigurations,validatingwebhookconfigurations`
lists them, and each one names the service it calls.

**List who holds which rights.** `kubectl get clusterrolebindings -o wide`
shows every subject bound for the whole cluster; an account of an application
namespace has no business there. `kubectl auth can-i --list --as
system:serviceaccount:facturation:<account>` tells what an identity can do,
and `kubectl get clusterrole <name> -o yaml` what a role grants. The `bind`
verb deserves attention: it lets someone hand out a role they do not hold.

**Read what changed recently.** `kubectl get events -n facturation
--sort-by=.lastTimestamp` shows Jobs created every minute. On a cluster whose
API server writes an audit log (lab `cks-audit-log-policy`), the log tells
which identity created `support-n2` and when: `jq 'select(.objectRef.name ==
"support-n2")'` on the log file. This lab's cluster does not audit by default,
so the events and the objects themselves are your evidence here.

**Record before removing.** `kubectl get <kind> <name> -o yaml >
/root/constat-persistance.yaml` keeps the object as the cluster knows it, with
its UID. Once deleted, nothing tells what it did any more.

**Remove in the right order.** First the mechanism, then what it grants:
deleting `support-n2` while its creator still runs only lasts a minute. Then
the identity that gave the mechanism its rights, then the access itself, and
finally the original Pod. Delete objects by name, one by one: deleting the
namespace, or every CronJob, would take the legitimate application with it.

**Check that nothing comes back.** Wait for the next minute, then ask again
`kubectl auth can-i list secrets -A --as
system:serviceaccount:facturation:support-n2`.

## How you will know it works

The tests read the record file and compare it with the UID of the object the
setup created, look for the CronJob, its Jobs and the attacker's bindings, wait
past the next minute of scheduling before judging that the access is gone, then
check the legitimate application, down to a real HTTP request on its Service.

```bash
dsoxlab check k8s-detecter-une-persistance
```
