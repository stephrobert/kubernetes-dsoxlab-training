# Challenge: A Job with parallel completions, and a CronJob

## 📍 The situation

In the **`lab`** namespace, the team has two batch processing needs.

The first one happens once: a task that must run **four times** successfully,
**two runs at a time**, and no more, because the database behind it cannot
handle more. Each run takes about ten seconds.

The second one comes back regularly: a cleanup to start **every five
minutes**. The team wants to keep the **last three** successful runs and the
**last** failed run, no more, so the namespace does not fill up.

## 🎯 What you must obtain

1. A Job **`batch-job`** in `lab`, image `busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4`, that runs four
   completions, two in parallel, each run lasting at least ten seconds before
   it succeeds.
2. The Job **completed successfully**, its four Pods in `Succeeded`, and the
   proof that two of them ran **at the same time**.
3. A CronJob **`log-cleanup`** in `lab`, image `busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4`,
   scheduled **every five minutes**, that keeps three successful Jobs and one
   failed Job.
4. A Job started **by hand from `log-cleanup`**, without waiting for its next
   run, completed successfully.

## 🧭 Useful landmarks

A Job says how many times to succeed, and how many at a time. Its Pods stay
after the end, with their start and end dates: that is how you know what
really overlapped.

A CronJob is just a Job template on a cron schedule, with two history
counters. It starts nothing before its next run, which may be far away: to try
it right away, you create a Job from it.

## ✅ How you will know it works

The tests read the Job, its Pods and their timestamps, the CronJob, then the
Job started by hand from it.

```bash
dsoxlab check ckad-job-cronjob
```
