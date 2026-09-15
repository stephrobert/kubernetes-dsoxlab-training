# Isolate the database: only the backend gets in

## The situation

In the namespace **`database`**, the database **`db`** listens on port 5432,
behind the Service of the same name. Two applications run alongside it:
**`backend`**, which needs the database, and **`frontend`**, which has no
business there. Today, everyone can connect to it, including from other
namespaces: a Pod named **`intrus`**, in the namespace `autre`, carries the
label `app=backend` and reaches the database without any trouble.

You are on the control plane, with `kubectl` configured.

## What you must achieve

1. A NetworkPolicy **`db-allow-backend`** in `database`, which applies to the
   database and lets in only the **`app=backend` Pods of the same
   namespace**, on port **5432** in TCP.

2. `backend` still reaches `db` on 5432.

3. `frontend` no longer manages to, and neither does `intrus`, despite its
   label.

4. The database can still **reach out**: it resolves names. The policy
   restricts only what comes in.

## Useful bearings

A NetworkPolicy selects Pods through `podSelector`, and says in `policyTypes`
what it controls, ingress, egress, or both. As soon as a Pod is selected for
ingress, everything the policy does not name is refused: that is what isolates.

A `from` rule with a `podSelector` alone only covers the namespace of the
policy. Adding an empty `namespaceSelector` to it opens up to every namespace:
that is the mistake that would let `intrus` in.

`kubectl exec backend -n database -- nc -z -w 3 db 5432` returns 0 if the
connection is established, and gives back the prompt after three seconds
otherwise.

## How you will know it works

The tests read the policy, then attempt the connections from `backend`,
`frontend` and `intrus`, and a name resolution from `db`.

```bash
dsoxlab check cka-networkpolicy-isolate-db
```
