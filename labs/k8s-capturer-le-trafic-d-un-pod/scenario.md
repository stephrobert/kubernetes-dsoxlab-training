# Capture the traffic of a Pod and name the cause of each failure

## The situation

In the namespace **`boutique`**, three client applications call their
service every two seconds:

| Client | Service it calls |
|---|---|
| `commandes` | `catalogue` |
| `factures` | `paiement` |
| `livraisons` | `transport` |

All three fail, each one in a different way, and their logs only say
`appel vers http://... en échec`. The team suspects three different causes:
a connection **refused**, packets **dropped** on the way, or a **DNS** name
that does not resolve. Nobody knows which client has which problem: the
packets will tell.

You are on the control plane, `k8s-cp.lab`, with `kubectl` configured. The
clients run on the two workers, `k8s-w1.lab` and `k8s-w2.lab`, and
`ssh k8s-w1.lab` opens a session on a worker. `tcpdump` is installed on the
three nodes.

## What you must achieve

1. For each client, a capture of its traffic, written with `tcpdump -w`,
   brought back to the control plane as **`~/captures/<client>.pcap`**
   (`~/captures/commandes.pcap`, and so on).
2. A file **`~/captures/diagnostic.yaml`** that names the cause of each
   failure, one line per client, with `refus`, `perte` or `dns`:

   ```yaml
   commandes: <cause>
   factures: <cause>
   livraisons: <cause>
   ```

3. **Nothing repaired.** The diagnosis is checked on the failures as the
   setup left them: a repaired failure fails the check.

## The method, step by step

1. **Find the Pod and its node**:
   `kubectl -n boutique get pods -o wide`. Note the address of each client
   Pod and the node it runs on.
2. **Pick a way to capture.** Three ways reach the same packets:
   - on the node, on the **host side interface** of the Pod. Calico names it
     `cali` followed by 11 characters; the route to the Pod address gives
     it: `ip route get <pod-ip>`;
   - on the node, **inside the network namespace of the Pod**: find the PID
     of its container with `crictl ps` and `crictl inspect`, then
     `nsenter -t <pid> -n tcpdump -i eth0 ...`. The tcpdump of the node is
     used, the Pod image does not need one;
   - from the control plane, with an **ephemeral container** that shares the
     network of the Pod: `kubectl debug` with an image that has tcpdump and
     the profile `netadmin`. Note that an ephemeral container stays listed
     in the Pod after it ends.
3. **Capture long enough**: a call that fails on DNS takes about 5 s before
   it gives up. 20 s cover several calls. Write the capture with `-w`, and
   keep every packet: DNS queries and TCP packets both matter.
4. **Bring the capture back** to the control plane:
   `scp k8s-w1.lab:/tmp/<file>.pcap ~/captures/<client>.pcap`.
5. **Read it**: `tcpdump -nn -r ~/captures/<client>.pcap`. For each client,
   ask three questions. Did the name resolve? Did a TCP SYN leave? What came
   back, and how fast?

## How you will know it works

`dsoxlab check k8s-capturer-le-trafic-d-un-pod` reads your captures on the
control plane with `tcpdump -r`. Each one must hold packets from the
**current** address of its Pod: a capture from an earlier `dsoxlab run`
names an address that no longer exists. Each one must also hold the packets
that prove the failure of its client. Then the check reads the three failures
in the cluster objects and compares them with your diagnosis.

The failures are drawn at random at each `dsoxlab run`: a diagnosis does not
carry over from one run to the next.
