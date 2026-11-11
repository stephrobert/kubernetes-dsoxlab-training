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

1. A Job **`batch-job`** in `lab`, image `busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4`, that runs four
   completions, two in parallel, each run lasting at least ten seconds
   before it succeeds.

2. The Job **completed successfully**, its four Pods in `Succeeded`, and the
   proof that two of them ran **at the same time**.

3. A CronJob **`log-cleanup`** in `lab`, image `busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4`, scheduled
   **every five minutes**, keeping three successful Jobs and one failed Job.

4. A Job started **by hand from `log-cleanup`**, without waiting for its next
   due time, completed successfully.

## Useful bearings

A Job describes how many times to succeed, and how many at a time. Its Pods
stay around after the end, with their start and end dates: that is how you
know what really overlapped.

A CronJob is nothing but a Job mould on a cron calendar, with two history
counters. It will not launch anything before its next due time, which may be
far off: to test it right away, you create a Job from it.

## How you will know it works

The tests read the Job, its Pods and their timestamps, the CronJob, then the
Job started by hand from it.

```bash
dsoxlab check ckad-job-cronjob
```
