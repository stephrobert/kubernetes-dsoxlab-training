# Challenge: Write a runbook that replays, and measure an application's SLO

## The situation

This morning, the team put a new image of the **`catalogue`** application into
production, in the namespace of the same name. Since then, it no longer
answers. The incident will happen again: someone other than you will have to
handle it, maybe at night, and they must be able to do it by running a single
command.

A probe checks the service's availability every minute. It wrote its last 30
days into **`/srv/catalogue/sonde.csv`**: one line per minute, `ok` when the
service answered, `ko` otherwise. The team set itself an availability objective
(SLO) of **99.5 %** over 30 days.

## What you must achieve

1. The **`catalogue`** application answers again, with its **two** replicas, on
   its **last good image**.

2. An executable runbook, **`~/runbooks/catalogue-indisponible.sh`**, brings the
   service back when the same incident happens again. The tests prove it by
   breaking the application again in the same way, then running it.

3. Run on a service **that works**, this runbook exits with **0** and **changes
   nothing**. A runbook looks at the state before acting.

4. A ConfigMap **`slo-catalogue`**, in the `catalogue` namespace, records:
   - `sli`: the availability measured over the 30 days of the journal, as a
     percentage with **two decimals** (for example `99.62`);
   - `slo`: the objective, `99.5`;
   - `budget-restant`: the error budget of the 30 days, minus the minutes of
     outage, in **whole minutes**. It is negative if the budget is overspent.

## Useful bearings

A Deployment keeps its previous revisions: `kubectl rollout history` lists
them, and the status of its Pods says why a revision does not start.

The error budget is what the objective allows you to miss: with a 99.5 % SLO,
it is 0.5 % of the window.

## How you will know it works

The tests run your runbook twice, under your account: once after breaking the
application again, once on a healthy service. They then recompute the SLI and
the budget from the preparation's draw: the number of minutes of outage changes
with every run.

```bash
dsoxlab check k8s-mesurer-un-slo-et-ecrire-un-runbook
```
