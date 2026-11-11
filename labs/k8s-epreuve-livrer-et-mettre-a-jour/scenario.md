# Level 1 test: ship and update an application

## The situation

The shop hands you its storefront, on the kind cluster **`boutique`** that your
`kubectl` already targets. The requirements say what to obtain, not how: it is
up to you to choose the resources. At the same time, the warehouse team tells
you that its **`stock`** component, in the **`entrepot`** space, no longer
starts.

The two versions of the storefront:

```text
version 1: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
version 2: nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
```

## The requirements

- The storefront lives in the space of its team, **`livraison`**, which you
  create, and **nothing** of it is left in the default space.
- It runs as **three copies**, which replace themselves if one disappears. It
  is shipped first as **version 1**.
- It answers HTTP at the address **`http://vitrine.livraison`** from any Pod of
  the cluster.
- It receives its welcome message, `Bienvenue`, in the variable
  **`MESSAGE_ACCUEIL`**, and the password of its database, `Boutique-2026`, in
  the variable **`DB_PASSWORD`**. The configuration and the password live
  **outside the image** and are managed **apart** from the storefront; the
  password **never appears in clear** in its description.
- It then moves to **version 2**, with no copy missing during the switch, and
  keeping the possibility to **go back to version 1**.
- **Before any repair**, write in **`~/epreuve/cause-stock.txt`** why the
  **`stock`** component does not start: what it looks for without finding it,
  and that it is missing, either through the state Kubernetes shows or in a
  sentence. Then leave that file untouched.
- The **`stock`** component runs again. It still reads its threshold, in the
  variable **`STOCK_SEUIL`**, from a configuration managed **apart** from its
  description, and that threshold is **`10`**.

## How you will be graded

The test is graded on the **final state of the cluster** and on the cause
file, never on the commands typed. It has **seven criteria**, all of equal
weight. The pass mark is **70 out of 100**, and **five criteria are critical**:
they must all pass, whatever the total. They are the storefront on version 2
with three copies, the address that answers, the configuration and the
password outside the image, the way back to version 1 kept open, and the
`stock` component repaired after its cause was recorded.

Passing the five critical criteria is therefore enough to pass the test; the
other two count in the score without changing the verdict. No procedure is
given, and the test offers **no hint**: the lessons of level 1 have taught
everything.

```bash
dsoxlab check  k8s-epreuve-livrer-et-mettre-a-jour
dsoxlab submit k8s-epreuve-livrer-et-mettre-a-jour
```
