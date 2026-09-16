# Serve a site over HTTPS with its own certificate, not the controller's

## The situation

The internal site **`vitrine.lab`** is published by the cluster's Ingress
controller. It answers, and it even answers over HTTPS: the team concluded
encryption was in place and closed the ticket.

The audit just reopened it. The controller builds a generic certificate at
startup and serves it to whoever asks, for want of having been given another
one. No client can therefore verify it is talking to `vitrine.lab`: the
certificate does not name that host, and nobody signed it.

The site lives in the **`vitrine`** namespace, behind a Service and an Ingress
already in place.

## What you must achieve

1. The server presents, for the `vitrine.lab` host, a certificate that **names
   that host**. It may be self-signed: there is no authority to reach here.

2. The site keeps answering. A TLS termination that breaks the route is no
   better than no termination at all.

The controller is already installed, leave it alone. Its secure entry point is
exposed on the node's port **30443**.

## Useful bearings

What the server presents is read on the connection itself, not in a manifest:

```bash
echo | openssl s_client -connect 127.0.0.1:30443 -servername vitrine.lab 2>/dev/null \
  | openssl x509 -noout -subject
```

The `-servername` option sends the requested name. Without it, the controller
does not know which host you want and falls back on its default certificate.

The certificate and its key go into an object whose **type** matters. An object
of the generic type carrying the same keys would be read by nobody.

A certificate carrying only a CN would be refused by any client that verifies:
TLS clients have ignored the CN for years and validate only the
`subjectAltName`.

Depositing the certificate is not enough: you must still **tell the Ingress**
to use it, and for which host.

The controller reloads its configuration after being notified. Give it a few
seconds before concluding.

## How you will know it works

The last test opens the connection and reads the certificate served, then
checks the site still answers. Both measurements are in the same test: "the
site answers over HTTPS" is already true before you intervene, and proves
nothing on its own.

```bash
dsoxlab check cks-ingress-tls
```
