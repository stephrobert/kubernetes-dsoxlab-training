# Capstone: bring the portal back, with nobody left to ask

## The situation

The team that ran the portal is gone. What they left fits in one sentence,
received by the on-call engineer: **"the production portal is not answering"**.
No ticket, no change log, nobody to call.

Everything happens in the **`production`** namespace. What sits there was
handed over in this state: there are faults, they are independent of one
another, and nothing here says which. Finding them is the exercise. Fixing
only one of them will make nothing answer.

Budget about **45 minutes**, and treat it as an exam: the pass mark is
**66 %**. One requirement fully satisfied is worth more than three half done.

## What is expected of you

1. **The portal runs in two copies**, and both are ready. It is called
   `portail`, and its image is the right one: that is not what you are being
   asked to change.

2. **The portal answers inside the cluster** at the name `portail-svc`, on
   port `80`.

3. **The portal answers on port `30080` of every node**, including from a
   machine that does not belong to the cluster. That is the access the team
   never put in place, and it is the one monitoring will check: it queries the
   nodes from the network, not from inside the cluster.

4. **The archive service has its storage.** The `portail-data` claim must
   actually be satisfied, and the `archives` Pod must be able to write in
   `/data`. A pending claim is not storage.

5. **You break nothing else.** The cluster must come out of this the way it
   went in, CoreDNS included.

## If you get stuck

A micro-lab gives you its bearings for free. A capstone does not: working out
where to look is exactly what it measures. This lab's four hints go from vague
to explicit, they **cost points**, and the first one names none of the three
faults: it only says where to start.

```bash
dsoxlab hint cka-capstone-portail
```

So the choice is yours, as it is on exam day: search, or pay to be pointed in
the right direction. Both are legitimate answers, and your score tells them
apart.

## How you will know it is done

The tests read the state of the cluster, never the commands you typed. The
last one is the only one that really proves anything: it queries the portal
from **each** of the two nodes, then from the machine driving the lab, which
is not part of the cluster. That is what monitoring will do.

```bash
dsoxlab check  cka-capstone-portail
dsoxlab submit cka-capstone-portail
```
