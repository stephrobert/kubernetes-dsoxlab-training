# Level 1 test: ship and update an application

## The situation

The shop asks you to ship its storefront on the kind cluster **`boutique`**,
which your `kubectl` already points at. The **`boutique`** namespace is
reserved for you, and it is empty. The requirements say what the storefront
must do, not how: choosing the resources is up to you.

The two versions of the storefront:

```text
version 1: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
version 2: nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
```

## The requirements

- The storefront runs as **three copies**, which replace themselves if one of
  them disappears. It is shipped first as **version 1**.
- It answers HTTP at **`http://vitrine.boutique`** from any Pod of the
  cluster.
- It receives its welcome message, `Bienvenue`, in the **`MESSAGE_ACCUEIL`**
  variable, and its database password, `Boutique-2026`, in the
  **`DB_PASSWORD`** variable. The configuration and the password are managed
  **apart** from the application, and the password **never appears in clear**
  in its description.
- It then moves to **version 2**, without any copy missing during the switch,
  and keeping the ability to **go back to version 1**.
- At the end, **nothing is in error** in the namespace.

## How you are graded

The test is graded on the **final state of the cluster**, never on the
commands typed or on your files. The pass mark is **70 out of 100**, and four
requirements are **critical**: they must all succeed, whatever the total. They
are the storefront on version 2 with three copies, the address that answers,
the configuration and password managed apart, and the way back to version 1.

No procedure is given: the level 1 lessons taught everything.

```bash
dsoxlab check  k8s-epreuve-livrer-et-mettre-a-jour
dsoxlab submit k8s-epreuve-livrer-et-mettre-a-jour
```
