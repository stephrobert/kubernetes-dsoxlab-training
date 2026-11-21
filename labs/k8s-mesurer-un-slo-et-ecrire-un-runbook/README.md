# Write a runbook that replays, and measure an application's SLO

The lesson defines the runbook, the SLI, the SLO and the error budget. This
course puts them into practice, with cases the lesson does not show: a runbook
fooled by the command it thought was safe, then fixed; an SLI and a budget
computed from a real journal; and the SLI of a short window, which does not
tell the same story as that of the whole window.

You work in a scratch namespace, `essai-slo`, with a `vitrine` ("showcase")
application, and trial files in your home directory. The challenge is about
other objects: you will do it on your own, at the end.

Related page (in French): [SRE et exploitation Kubernetes au quotidien](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/sre-exploitation-kubernetes/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-mesurer-un-slo-et-ecrire-un-runbook
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

Create the trial application:

```bash
kubectl create namespace essai-slo; kubectl create deployment vitrine --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb -n essai-slo; kubectl rollout status deployment/vitrine -n essai-slo --timeout=120s
```

```text
namespace/essai-slo created
deployment.apps/vitrine created
Waiting for deployment "vitrine" rollout to finish: 0 of 1 updated replicas are available...
deployment "vitrine" successfully rolled out
```

## 📒 Exercise 1: a runbook fooled, then fixed

A runbook must be able to replay: on a healthy service, it does nothing. So it
starts by looking at the state. Here is a first version, which trusts `kubectl
rollout status`. Break `vitrine` by removing all its replicas, then run the
runbook (`rien à faire` means "nothing to do"):

```bash
cat > ~/essai-runbook.sh <<'RB'
#!/usr/bin/env bash
# Runbook d'essai, version 1 : il croit rollout status.
if kubectl -n essai-slo rollout status deployment/vitrine --timeout=10s >/dev/null 2>&1; then
  echo "vitrine disponible : rien à faire"; exit 0
fi
kubectl -n essai-slo scale deployment/vitrine --replicas=1
RB
chmod +x ~/essai-runbook.sh; kubectl -n essai-slo scale deployment/vitrine --replicas=0; ~/essai-runbook.sh; kubectl -n essai-slo get deployment vitrine
```

```text
deployment.apps/vitrine scaled
vitrine disponible : rien à faire
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
vitrine   0/0     0            0           0s
```

The runbook says "nothing to do" while no Pod runs any more: `0/0`. `rollout
status` answers "success" because the Deployment has as many available
replicas as requested, that is zero. The command that looked safe does not see
this incident. Version 2 counts the available replicas (`aucun réplica
disponible : remise à 1` means "no replica available: back to 1"):

```bash
cat > ~/essai-runbook.sh <<'RB'
#!/usr/bin/env bash
# Runbook d'essai, version 2 : il compte les réplicas disponibles.
dispo=$(kubectl -n essai-slo get deployment vitrine -o jsonpath='{.status.availableReplicas}')
if [ "${dispo:-0}" -ge 1 ]; then
  echo "vitrine disponible ($dispo) : rien à faire"; exit 0
fi
echo "aucun réplica disponible : remise à 1"
kubectl -n essai-slo scale deployment/vitrine --replicas=1
kubectl -n essai-slo rollout status deployment/vitrine --timeout=120s
RB
~/essai-runbook.sh
```

```text
aucun réplica disponible : remise à 1
deployment.apps/vitrine scaled
Waiting for deployment "vitrine" rollout to finish: 0 of 1 updated replicas are available...
deployment "vitrine" successfully rolled out
```

This time, the runbook sees the incident and fixes it. Replay it on the service
that works again:

```bash
~/essai-runbook.sh; kubectl -n essai-slo get deployment vitrine
```

```text
vitrine disponible (1) : rien à faire
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
vitrine   1/1     1            1           1s
```

It sees the healthy state and touches nothing. This is how a runbook is
tested: on the incident it must handle, then on a service that works.

## 📈 Exercise 2: an SLI computed from a journal

A probe checked `vitrine` every minute for one day. Build its journal: one line
per minute, with a 9-minute outage.

```bash
python3 -c "
import datetime
d = datetime.datetime(2026, 11, 20)
ko = set(range(600, 609))
print('horodatage,statut')
for m in range(1440):
    print(f'{d + datetime.timedelta(minutes=m):%Y-%m-%dT%H:%MZ},' + ('ko' if m in ko else 'ok'))
" > ~/essai-sonde.csv; wc -l < ~/essai-sonde.csv; grep -c ',ko' ~/essai-sonde.csv
```

```text
1441
9
```

1,441 lines: the header and 1,440 minutes, 9 of them in outage. The
availability SLI is the share of minutes when the service answered (`en panne`
means "in outage"):

```bash
awk -F, 'NR>1 {t++; if ($2 == "ko") k++} END {printf "minutes %d, en panne %d, SLI %.2f %%\n", t, k, (t-k)/t*100}' ~/essai-sonde.csv
```

```text
minutes 1440, en panne 9, SLI 99.38 %
```

For a 99.9 % SLO over this day, the error budget is 0.1 % of the minutes
(`consommé` means "spent", `restant` "left"):

```bash
awk -F, 'NR>1 {t++; if ($2 == "ko") k++} END {b = t*0.1/100; printf "budget %.2f min, consommé %d min, restant %.2f min\n", b, k, b-k}' ~/essai-sonde.csv
```

```text
budget 1.44 min, consommé 9 min, restant -7.56 min
```

The budget is overspent: a single 9-minute outage uses six times what the
objective allows in a day. A 99.9 % SLO leaves only a minute and a half per
day.

## 🔎 Exercise 3: a short window, another story

Now measure the SLI over the 20 minutes around the outage:

```bash
sed -n '597,616p' ~/essai-sonde.csv | awk -F, '{t++; if ($2 == "ko") k++} END {printf "20 minutes autour de la panne : SLI %.2f %%\n", (t-k)/t*100}'
```

```text
20 minutes autour de la panne : SLI 55.00 %
```

55 % over 20 minutes, 99.38 % over the day: the same outage, two figures. An
SLI only makes sense with its window. The short window says to act now; the
long window says whether the objective is met.

## 🧹 Clean-up

Delete the namespace and the trial files:

```bash
kubectl delete namespace essai-slo; rm -f ~/essai-runbook.sh ~/essai-sonde.csv
```

```text
namespace "essai-slo" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-mesurer-un-slo-et-ecrire-un-runbook
dsoxlab check k8s-mesurer-un-slo-et-ecrire-un-runbook
```

```text
╭─ Result: k8s-mesurer-un-slo-et-ecrire-un-runbook ─╮
│  0 / 100 pts                                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests                  │
╰───────────────────────────────────────────────────╯
```

0 out of 5: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: an application down after a release, a
runbook to write for next time, and 30 days of probe to measure against their
objective.

```bash
dsoxlab run k8s-mesurer-un-slo-et-ecrire-un-runbook
dsoxlab challenge k8s-mesurer-un-slo-et-ecrire-un-runbook
```
