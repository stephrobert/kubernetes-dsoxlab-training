# Route two applications on a single host, and prove each gets its own

## The situation

Two applications live in the **`lab`** namespace and already serve: the API and
the site. Each has its Service, `svc-api` and `svc-web`, on port `80`.

The team has only one hostname, **`app.local`**, and must publish both behind
it. Today nothing does: the Ingress controller is listening, but no rule tells
it where to send what.

Each application answers with its own name, which lets you check unambiguously
which one replied.

## What you must achieve

For the `app.local` host:

1. Requests whose path starts with **`/api`** reach `svc-api`.

2. Requests whose path starts with **`/web`** reach `svc-web`.

3. A path you did not declare reaches **neither**.

The controller is already installed, leave it alone. Its HTTP entry point is
exposed on the node's port **30080**.

## Useful bearings

Since nothing is published, requests are made by telling `curl` where to reach
the host:

```bash
curl -s --resolve app.local:30080:127.0.0.1 http://app.local:30080/api
```

The object describing these rules lives in the **same namespace** as the
Services it routes. That is not a detail: it cannot designate one elsewhere.

Name its **class**. Depending on the controller and its settings, an object
without a class may be served anyway, or ignored: naming the class makes the
choice of controller explicit, and depends on none of those settings.

The **path type** matters: the one comparing a prefix accepts `/api` as well as
`/api/v1`, while the one comparing exactly would accept only `/api`.

The controller reloads its configuration after being notified. Give it a few
seconds.

## How you will know it works

One test reads the rule, then one test per path queries all **three** paths.
The undeclared path is the control: a single rule sending everything to one
service would pass the other two measurements without routing anything.

```bash
dsoxlab check cka-ingress-path-routing
```
