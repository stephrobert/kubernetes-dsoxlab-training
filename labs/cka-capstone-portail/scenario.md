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

3. **The portal answers from outside the cluster**, on port **30080** of
   **every** node. That is the access the team never put in place, and it is
   the one monitoring will check.

4. **The archive service has its storage.** The `portail-data` claim must
   actually be satisfied, and the `archives` Pod must be able to write in
   `/data`. A pending claim is not storage.

5. **You break nothing else.** The cluster must come out of this the way it
   went in, CoreDNS included.

## Useful bearings

Nothing here says where the faults are. These are the reflexes that find them.

- A Pod that does not start always says why, but rarely in `kubectl get`.
  `kubectl describe pod`, and above all the *Events* section at the bottom,
  are more talkative, and `kubectl get events --sort-by=.lastTimestamp` gives
  the order in which things happened.
- A Service that does not answer has either no endpoint, or the wrong ones.
  `kubectl get endpointslice` says which of the two, and that is a different
  diagnosis each time.
- A node has a finite amount of CPU and memory, which `kubectl describe node`
  shows, along with what is already reserved.
- A pending volume claim is looking for something that does not exist.
  `kubectl describe pvc` says what it is looking for.

## How you will know it is done

The tests read the state of the cluster, never the commands you typed. The
last one is the only one that really proves anything: it queries the portal
from **each** of the two nodes, the way monitoring will.

```bash
dsoxlab check  cka-capstone-portail
dsoxlab submit cka-capstone-portail
```
