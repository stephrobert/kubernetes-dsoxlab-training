# Capstone: open an enclave for a team you do not trust

## The situation

An outside team is about to ship an application into your cluster. The
contract is signed, the date is set, and you will not know what they deploy
until they deploy it.

You are asked to open them a space, **`enclave`**, that stays safe even if they
are not. The rule security gave you fits in one sentence: whatever protects
that space must hold without anyone reviewing their manifests.

Two witnesses are already in place, and they are not yours: an **`autorise`**
Pod in `enclave`, carrying the `role=appelant` label, and an **`intrus`** Pod
in the `dehors` namespace. Leave them alone, they are there to measure.

Count about **45 minutes**, and treat this as the exam: the pass mark is
**66 %**. One fully satisfied requirement beats three half-done.

## What is expected of you

1. **The cluster itself refuses what must not enter the enclave.** Any
   workload asking for privileges, kernel or machine access must be rejected
   **at creation time**, by the cluster, not by a human review. The rejection
   must be explained to whoever hits it, and leave a trace for whoever audits.

2. **The application has an identity of its own**, called `coffre`, and that
   identity's token is **never deposited** into the workloads using it.

3. **That identity can only list the workloads of its own space.** Nothing
   else: not reading secrets, not creating or deleting anything, not seeing
   what happens in other spaces.

4. **A workload named `coffre` runs in the enclave**, uses that identity, and
   serves a page. It is reached inside the cluster under the name `coffre`, on
   port `80`.

5. **Nothing reaches `coffre` from outside the enclave.** Only enclave
   workloads carrying the `role=appelant` label get through. The `autorise`
   Pod must keep getting through: you are not asked for an outage, you are
   asked for a boundary.

## If you get stuck

A micro-lab gives you its bearings for free. A capstone does not: deciding
**what to put in place** is exactly what it measures. The four hints go from
vaguest to most explicit, they **cost points**, and the first one names no
object: it only says what to look at first.

```bash
dsoxlab hint cks-capstone-enclave
```

## How you will know it works

Two of the five tests do not settle for re-reading what you put in place: they
**attempt** what must be refused. A mistyped setting is accepted without
complaint by the cluster and refuses nothing; a rule whose selector designates
nobody is a perfectly valid object that protects nothing.

```bash
dsoxlab check cks-capstone-enclave
```
