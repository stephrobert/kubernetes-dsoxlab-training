# Challenge: Run one-off and scheduled tasks

## 📍 The situation

The accounting department hands three jobs over to the kubeadm cluster, in
the **`compta`** namespace. You are on the control plane, with `kubectl`
configured.

- The **`lots`** ConfigMap lists the invoice lots of the day: one
  **`lot-<index>`** key per lot, starting with `lot-0`. Their number changes
  from one day to the next.
- The **`export-config`** ConfigMap holds the period to export.
- The **`export-compta`** Job failed last night.

Every task uses the image
`busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4`.

## 🎯 What you must obtain

1. A Job **`facturer-lots`** that processes **each lot once**: as many
   completions as lots, each Pod takes the lot of **its own number** and
   writes a line **`lot <index> : <lot name>`** to its logs. The Job
   completes successfully. **Blocking requirement.**
2. `facturer-lots` runs **two** Pods at a time and allows **only one** retry.
3. A CronJob **`relance-impayes`** runs **Monday to Friday at 6:15, Paris
   time**. A run that starts replaces one that would still be running. It
   keeps **three** successful Jobs and **two** failed ones, and gives up a run
   that would be more than **five minutes** late. **Blocking requirement.**
4. A run of `relance-impayes`, **started by hand** without waiting for the
   schedule, has completed.
5. `export-compta` has been **recreated** and has completed: it exports the
   period that `export-config` holds.

## 🧭 Useful landmarks

Do not delete the Pods of the Jobs once they are finished: their logs are the
evidence.

## ✅ How you will know it works

The tests read the Jobs, their Pods and their logs, and the CronJob. The
number of lots and their names are drawn at random during the preparation.
The pass mark is 80%, and both blocking requirements must be met.

```bash
dsoxlab check k8s-challenge-executer-et-planifier-des-taches
```
