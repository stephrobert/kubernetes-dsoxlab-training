# A Job with parallel completions, and a CronJob

## The situation

In the **`lab`** namespace, the team has two batch processing needs.

The first is one-off: a workload that must run **four times** successfully,
**two runs at a time**, and no more, because the database behind it cannot
take any more than that. Each run takes about ten seconds.

The second is recurring: a cleanup to launch **every five minutes**, for
which the team wants to keep a trace of the **last three** successful runs
and the **last** failed run, no more, so the namespace does not fill up.

## What you must achieve

1. A Job **`batch-job`** in `lab`, image `busybox:1.36`, that runs four
   completions, two in parallel, each run lasting at least ten seconds
   before it succeeds.

2. The Job **completed successfully**, its four Pods in `Succeeded`, and the
   proof that two of them ran **at the same time**.

3. A CronJob **`log-cleanup`** in `lab`, image `busybox:1.36`, scheduled
   **every five minutes**, keeping three successful Jobs and one failed Job.

## Useful bearings

A Job describes how many times to succeed, and how many at a time. Its Pods
stay around after the end, with their start and end dates: that is how you
know what really overlapped.

A CronJob is nothing but a Job mould on a cron calendar, with two history
counters. It will not launch anything before its next due time, and that is
fine: what is checked here is its definition.

## How you will know it works

The tests read the Job, its Pods and their timestamps, then the CronJob.

```bash
dsoxlab check ckad-job-cronjob
```
