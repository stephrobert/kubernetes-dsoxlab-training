# Forbid everything, then reopen the strict minimum, DNS included

## The situation

In the **`zero-confiance`** namespace, four Pods talk freely: **`db`** serves
HTTP on port 80, **`annuaire`** does too, **`web`** is the database's
legitimate client, and **`intrus`** has no business touching it. No network
policy exists, so everyone reaches everyone, `intrus` included.

The audit mandates the **zero-trust** model: close everything, then reopen
what the application needs, and **nothing else**.

## What you must achieve

1. The namespace denies **by default** all inbound and all outbound traffic,
   for **every** one of its Pods.

2. The only application flow allowed is **`web` to `db` on port 80**.

3. **Pods still resolve names.** That is a requirement in its own right: an
   application that resolves nothing is down, even if its flows are allowed.

4. Nothing else goes through. `intrus` does not reach `db`, `web` does not
   reach `annuaire`, and `db` goes nowhere on its own initiative.

## Useful bearings

A NetworkPolicy only states what it **allows**, in the directions it declares
under `policyTypes`. Declaring a direction without writing a single rule for
it forbids it entirely; not declaring it says nothing about it, so everything
goes through.

An empty `podSelector` selects **every** Pod in the namespace.

Policies **add up**: a Pod is reachable if at least one rule allows it. There
is no explicit deny rule, which means an over-broad policy is not fixed by
adding a prohibition, but by narrowing it.

## How you will know it works

The tests make real connections between the Pods. Each checks **both
directions** in the same measurement, because without a policy everything goes
through and after a blanket cut everything is blocked: only the pair shows
that sorting happens.

```bash
dsoxlab check cks-networkpolicy-default-deny
```
