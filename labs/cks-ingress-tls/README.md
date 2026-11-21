# Serve a site over HTTPS with its own certificate, not the controller's

The lesson shows an Ingress that serves an application over HTTPS with a
certificate stored in a Secret. This course has you check which certificate
the controller really serves, and adds cases the lesson does not show: the
certificate Traefik serves when it finds none, a certificate without a SAN, a
key that does not match its certificate, a certificate replaced live, a
wildcard certificate and its limit, and the redirection from HTTP to HTTPS.

You work in a scratch namespace, `essai-tls`, with an application `kiosque`
("kiosk", nginx) and hosts under `salon.lab`. The certificates are created in
the `~/essai-tls` directory. The challenge is about other objects: you will do
it on your own, at the end.

Related page: [Ingress](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/ingress/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-ingress-tls
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

Traefik listens over HTTPS on port 30443 of every node, and over HTTP on port
30080. To call a host such as `kiosque.salon.lab` without touching DNS, this
course uses curl's `--resolve` option: it tells curl which address to use for
that name.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2 and Traefik v3.7.

Create the namespace, the working directory and the application:

```bash
kubectl create namespace essai-tls; mkdir -p ~/essai-tls
kubectl run kiosque --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb -n essai-tls --labels=app=kiosque; kubectl expose pod kiosque --port=80 -n essai-tls; kubectl wait --for=condition=Ready pod/kiosque -n essai-tls --timeout=120s
```

```text
namespace/essai-tls created
pod/kiosque created
service/kiosque exposed
pod/kiosque condition met
```

## 🔎 Exercise 1: which certificate does the controller serve?

Make a self-signed certificate that names the host only in its CN field (the
common name), then display its subject and its SANs (the alternative names,
the `subjectAltName` extension):

```bash
cd ~/essai-tls && openssl req -x509 -newkey rsa:2048 -nodes -days 30 -subj '/CN=kiosque.salon.lab' -keyout cn.key -out cn.crt 2>/dev/null && openssl x509 -in cn.crt -noout -subject -ext subjectAltName
```

```text
No extensions in certificate
subject=CN = kiosque.salon.lab
```

The certificate has no extension, hence no SAN. Store it in a TLS Secret and
create an HTTPS Ingress that uses it:

```bash
kubectl create secret tls kiosque-cn -n essai-tls --cert=$HOME/essai-tls/cn.crt --key=$HOME/essai-tls/cn.key; cat <<'YAML' | kubectl apply -n essai-tls -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: kiosque
spec:
  ingressClassName: traefik
  tls:
    - hosts: [kiosque.salon.lab]
      secretName: kiosque-cn
  rules:
    - host: kiosque.salon.lab
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service: {name: kiosque, port: {number: 80}}
YAML
```

```text
secret/kiosque-cn created
ingress.networking.k8s.io/kiosque created
```

Ask the controller for the certificate it presents for this host. The
`-servername` option sends the requested name (the SNI): this is what lets
Traefik choose the certificate:

```bash
sleep 3; echo | openssl s_client -connect 127.0.0.1:30443 -servername kiosque.salon.lab 2>/dev/null | openssl x509 -noout -subject
```

```text
subject=CN = kiosque.salon.lab
```

It is yours. Now ask for a host that nothing declares:

```bash
echo | openssl s_client -connect 127.0.0.1:30443 -servername inconnu.salon.lab 2>/dev/null | openssl x509 -noout -subject
```

```text
subject=CN = TRAEFIK DEFAULT CERT
```

For a name it does not know, Traefik serves its own certificate, `TRAEFIK
DEFAULT CERT`. If a client sees this name, Traefik found no certificate for
the requested host: missing Secret, wrong name, or host missing from the
Ingress's `tls` section.

Call the site with curl, giving it your certificate as the trusted authority
(`--cacert`):

```bash
curl -sS -o /dev/null -w '%{http_code}\n' --cacert ~/essai-tls/cn.crt --resolve kiosque.salon.lab:30443:127.0.0.1 "https://kiosque.salon.lab:30443/"; echo "curl : code $?"
```

```text
200
curl : code 0
```

curl accepts this certificate without a SAN: it falls back to the CN. Current
browsers and programs written in Go reject such a certificate. A curl test is
therefore not enough: always create your certificates with a SAN, as in
exercise 3.

## 🔑 Exercise 2: a key that does not match the certificate

Make a certificate with a SAN, then another, unrelated key. Try to store the
certificate with the wrong key:

```bash
cd ~/essai-tls && openssl req -x509 -newkey rsa:2048 -nodes -days 30 -subj '/CN=kiosque.salon.lab' -addext 'subjectAltName=DNS:kiosque.salon.lab' -keyout san.key -out san.crt 2>/dev/null && openssl genrsa -out autre.key 2048 2>/dev/null; kubectl create secret tls kiosque-melange -n essai-tls --cert=$HOME/essai-tls/san.crt --key=$HOME/essai-tls/autre.key
```

```text
error: tls: private key does not match public key
```

`kubectl create secret tls` refuses: the private key does not match the
certificate's public key. This check is done by that command. A Secret written
in YAML and sent with `kubectl apply` skips it, and the error would then only
show when Traefik tries to use it.

## 🔄 Exercise 3: replace the certificate live

Replace the content of the `kiosque-cn` Secret with the certificate that has
a SAN and its right key. `--dry-run=client -o yaml` builds the Secret without
sending it, and `kubectl replace` replaces the old one:

```bash
kubectl create secret tls kiosque-cn -n essai-tls --cert=$HOME/essai-tls/san.crt --key=$HOME/essai-tls/san.key --dry-run=client -o yaml | kubectl replace -f -; sleep 5; curl -sS -o /dev/null -w '%{http_code}\n' --cacert ~/essai-tls/san.crt --resolve kiosque.salon.lab:30443:127.0.0.1 https://kiosque.salon.lab:30443/
```

```text
secret/kiosque-cn replaced
200
```

Traefik picked up the new certificate in under 5 seconds, without restarting
and without touching the Ingress. This is how a certificate is renewed. Read
its validity dates, straight from the connection:

```bash
echo | openssl s_client -connect 127.0.0.1:30443 -servername kiosque.salon.lab 2>/dev/null | openssl x509 -noout -dates
```

```text
notBefore=Nov 21 00:03:53 2026 GMT
notAfter=Dec 21 00:03:53 2026 GMT
```

`notAfter` is the expiry date, 30 days after creation (`-days 30`). Reading
the dates from what the controller serves, and not from the file, proves that
the new certificate is the one in service.

## 🃏 Exercise 4: one certificate for all the hosts of a domain

Make a wildcard certificate, valid for `*.salon.lab`, and store it in a new
Secret:

```bash
cd ~/essai-tls && openssl req -x509 -newkey rsa:2048 -nodes -days 30 -subj '/CN=*.salon.lab' -addext 'subjectAltName=DNS:*.salon.lab' -keyout joker.key -out joker.crt 2>/dev/null; kubectl create secret tls salon-joker -n essai-tls --cert=$HOME/essai-tls/joker.crt --key=$HOME/essai-tls/joker.key
```

```text
secret/salon-joker created
```

Have it served for three hosts: `kiosque.salon.lab`, `accueil.salon.lab` and
`a.b.salon.lab`, with a rule for each one:

```bash
kubectl patch ingress kiosque -n essai-tls --type json -p '[{"op":"replace","path":"/spec/tls","value":[{"hosts":["kiosque.salon.lab","accueil.salon.lab","a.b.salon.lab"],"secretName":"salon-joker"}]},{"op":"add","path":"/spec/rules/-","value":{"host":"accueil.salon.lab","http":{"paths":[{"path":"/","pathType":"Prefix","backend":{"service":{"name":"kiosque","port":{"number":80}}}}]}}},{"op":"add","path":"/spec/rules/-","value":{"host":"a.b.salon.lab","http":{"paths":[{"path":"/","pathType":"Prefix","backend":{"service":{"name":"kiosque","port":{"number":80}}}}]}}}]'; sleep 5
```

```text
ingress.networking.k8s.io/kiosque patched
```

Call the first two:

```bash
for h in kiosque.salon.lab accueil.salon.lab; do printf '%s -> ' $h; curl -sS -o /dev/null -w '%{http_code}\n' --cacert ~/essai-tls/joker.crt --resolve $h:30443:127.0.0.1 "https://$h:30443/"; done
```

```text
kiosque.salon.lab -> 200
accueil.salon.lab -> 200
```

A single certificate covers both hosts. Now look at the one `a.b.salon.lab`
receives:

```bash
echo | openssl s_client -connect 127.0.0.1:30443 -servername a.b.salon.lab 2>/dev/null | openssl x509 -noout -subject
```

```text
subject=CN = TRAEFIK DEFAULT CERT
```

```bash
printf 'a.b.salon.lab -> '; curl -sS -o /dev/null -w '%{http_code}\n' --cacert ~/essai-tls/joker.crt --resolve a.b.salon.lab:30443:127.0.0.1 "https://a.b.salon.lab:30443/"; echo "curl : code $?"
```

```text
a.b.salon.lab -> curl: (60) SSL certificate problem: self-signed certificate
More details here: https://curl.se/docs/sslcerts.html

curl failed to verify the legitimacy of the server and therefore could not
establish a secure connection to it. To learn more about this situation and
how to fix it, please visit the web page mentioned above.
000
curl : code 60
```

The `*` wildcard covers a single level only: `a.salon.lab`, but not
`a.b.salon.lab`. Traefik therefore finds no certificate for that name, despite
the Ingress's `tls` section, and serves its own. curl rejects it (code 60). A
two-level subdomain needs one more SAN in the certificate.

## ↪️ Exercise 5: send HTTP to HTTPS

For now, the site also answers over plain HTTP:

```bash
curl -s -o /dev/null -w '%{http_code}\n' --resolve kiosque.salon.lab:30080:127.0.0.1 http://kiosque.salon.lab:30080/
```

```text
200
```

The standard Ingress cannot ask for a redirection. With Traefik, it goes
through a Traefik resource, a Middleware, attached to the Ingress with an
annotation. The name to give in the annotation is
`<namespace>-<name>@kubernetescrd`:

```bash
cat <<'YAML' | kubectl apply -n essai-tls -f -
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: vers-https
spec:
  redirectScheme:
    scheme: https
    port: "30443"
    permanent: true
YAML
kubectl annotate ingress kiosque -n essai-tls traefik.ingress.kubernetes.io/router.middlewares=essai-tls-vers-https@kubernetescrd; sleep 5
```

```text
middleware.traefik.io/vers-https created
ingress.networking.k8s.io/kiosque annotated
```

Call the site over HTTP again:

```bash
curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' --resolve kiosque.salon.lab:30080:127.0.0.1 http://kiosque.salon.lab:30080/
```

```text
301 https://kiosque.salon.lab:30443/
```

`301` and the HTTPS address: the client is sent to port 30443.
`permanent: true` gives a 301, which browsers remember. Without it, the
redirection is temporary, which is safer while you experiment.

## 🧹 Clean-up

Delete the scratch namespace and the certificates directory:

```bash
kubectl delete namespace essai-tls; rm -rf ~/essai-tls
```

```text
namespace "essai-tls" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cks-ingress-tls
dsoxlab check cks-ingress-tls
```

```text
╭───── Result: cks-ingress-tls ─────╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests  │
╰───────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a site to serve over HTTPS with its own
certificate, and the proof that the controller presents yours.

```bash
dsoxlab run cks-ingress-tls
dsoxlab challenge cks-ingress-tls
```
