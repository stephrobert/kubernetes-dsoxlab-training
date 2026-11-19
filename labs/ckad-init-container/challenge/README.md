# Challenge: Wait for a dependency with an init container

## 📍 The situation

In the **`lab`** namespace, the **`app`** application reads its configuration
at startup from an internal server, exposed by the **`config-svc`** Service on
port 80. When that server is not there, the application starts anyway, with no
configuration. It then behaves badly for hours before anyone notices.

The team wants the application to **go no further as long as `config-svc` does
not answer**. The Service already exists, but nothing runs behind it for now.
That is the starting situation, and it is the one you must know how to handle.

## 🎯 What you must obtain

1. A Pod **`app`** in `lab`, with an init container named
   **`wait-for-config`** that waits until `http://config-svc/` answers, then a
   main container named **`main`**, image `nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb`.
2. As long as nothing answers behind `config-svc`, the Pod `app` stays in
   **`Init`**: see it for yourself.
3. A Pod **`config-server`** in `lab`, image `nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb`, with the
   label **`app=config`**, which the `config-svc` Service selects.
4. Once `config-server` is ready, the init container finishes and `app` moves
   to `Running` without you doing anything else.

## 🧭 Useful landmarks

An init container runs before the main containers, all the way through, and
the Pod waits until it succeeds. An `until` loop with `wget` makes a very good
guard, in the image
`busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4`.

A Service resolves in DNS as soon as it exists, even with no address behind
it: waiting for the name to resolve waits for nothing. Waiting for an HTTP
answer does.

## ✅ How you will know it works

The tests read the definition of the Pod `app`, the addresses of the Service,
and the state of the init container, which must have finished successfully.

```bash
dsoxlab check ckad-init-container
```
