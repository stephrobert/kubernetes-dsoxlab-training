# Bring a broken application and its cluster back into service

## The situation

Monday, 8 a.m. Over the weekend, several people "fixed things" on the kubeadm
cluster of the shop, and this morning nothing works:

- in the **`commerce`** namespace, the **`api`** application restarts in a
  loop, and the **`vitrine`** Pod never starts;
- **`kubectl`** gets no answer any more;
- the worker **`k8s-w1.lab`** has dropped out of the cluster, and the
  **`entrepot`** application, which is reserved for it, is down with it.

You are on the control plane. As in the exam, `ssh k8s-w1.lab` opens a session
on the worker. No procedure is given: the module taught you the method.

## What you must achieve

1. The **`api`** Deployment has its **two replicas available**.
2. **No Pod** of `api` restarts in a loop any more.
3. `api` reads its configuration where the team's convention puts it: the
   **`APP_CONFIG_PATH`** variable is **`/etc/config`**, the application really
   finds its **`app.conf`** file there, and it **answers** on its port.
4. The **`vitrine`** Pod runs a **public nginx image**, really pulled by the
   node, and **answers in HTTP**.
5. **Before repairing a failure**, you write its cause in a file of
   **`~/incident/`**, one per failure: **`api.txt`**, **`vitrine.txt`**,
   **`apiserver.txt`** and **`kubelet.txt`**. The cause comes from what you
   read (`describe`, the events, the logs): it **names what is wrong**, not
   only the status Kubernetes shows. Then leave each file untouched: its date
   is compared with the start of what was repaired.
6. The **API server** answers again, and its Pod runs without restarting in a
   loop.
7. Its **manifest** no longer carries the faulty flag, and still authorizes
   requests with **`Node,RBAC`**.
8. **`k8s-w1.lab`** is **`Ready`**, and its kubelet runs with a **valid**
   configuration that keeps the address of the cluster DNS.
9. The kubelet of the worker is **active**, and will **start again after a
   reboot** of the machine.
10. **`entrepot`** has its **three replicas available** again, on
    `k8s-w1.lab`.

The repairs are made on what describes the application or the node (the
Deployment, the manifest, the configuration of the service), not by removing
what is in the way: fewer replicas, a deleted line or an application moved to
another node repair nothing.

## How you will be graded

Ten states, equally weighted. The pass mark is **70 out of 100**, and two
states are **blocking**: the causes recorded before the repairs (state 5) and
the API server back in service (state 6). Passing the others does not make up
for missing one of them.

The tests read the cluster through its API, the state of the services and the
files on the nodes, and the dates of your files in `~/incident/`. The feedback
is limited to the verdict: passed or not, and the score.

```bash
dsoxlab check  k8s-challenge-depanner-une-application
dsoxlab submit k8s-challenge-depanner-une-application
```
