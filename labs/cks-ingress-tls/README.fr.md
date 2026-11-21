# Servir un site en HTTPS avec son propre certificat, et non celui du contrôleur

La leçon montre un Ingress qui sert une application en HTTPS avec un
certificat rangé dans un Secret. Ce cours vous fait vérifier quel certificat
le contrôleur sert vraiment, et ajoute des cas que la leçon ne montre pas : le
certificat que Traefik sert quand il n'en trouve aucun, un certificat sans
SAN, une clé qui ne va pas avec son certificat, un certificat remplacé à
chaud, un certificat wildcard et sa limite, et la redirection de HTTP vers
HTTPS.

Vous travaillez dans un namespace d'essai, `essai-tls`, avec une application
`kiosque` (nginx) et des hôtes en `salon.lab`. Les certificats sont créés dans
le répertoire `~/essai-tls`. Le challenge porte sur d'autres objets : vous le
ferez seul, à la fin.

Page associée : [Ingress](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/ingress/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-ingress-tls
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Traefik écoute en HTTPS sur le port 30443 de chaque nœud, et en HTTP sur le
port 30080. Pour appeler un hôte comme `kiosque.salon.lab` sans toucher au
DNS, ce cours utilise l'option `--resolve` de curl : elle dit à curl quelle
adresse utiliser pour ce nom.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2 et Traefik v3.7.

Créez le namespace, le répertoire de travail et l'application :

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

## 🔎 Exercice 1 : quel certificat le contrôleur sert-il ?

Fabriquez un certificat autosigné qui nomme l'hôte uniquement dans son
champ CN (le nom commun), puis affichez son sujet et ses SAN (les noms
alternatifs, l'extension `subjectAltName`) :

```bash
cd ~/essai-tls && openssl req -x509 -newkey rsa:2048 -nodes -days 30 -subj '/CN=kiosque.salon.lab' -keyout cn.key -out cn.crt 2>/dev/null && openssl x509 -in cn.crt -noout -subject -ext subjectAltName
```

```text
No extensions in certificate
subject=CN = kiosque.salon.lab
```

Le certificat n'a aucune extension, donc aucun SAN. Rangez-le dans un Secret
de type TLS et créez un Ingress HTTPS qui l'utilise :

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

Demandez au contrôleur le certificat qu'il présente pour cet hôte. L'option
`-servername` envoie le nom demandé (le SNI) : c'est lui qui permet à Traefik
de choisir le certificat :

```bash
sleep 3; echo | openssl s_client -connect 127.0.0.1:30443 -servername kiosque.salon.lab 2>/dev/null | openssl x509 -noout -subject
```

```text
subject=CN = kiosque.salon.lab
```

C'est bien le vôtre. Demandez maintenant un hôte que rien ne déclare :

```bash
echo | openssl s_client -connect 127.0.0.1:30443 -servername inconnu.salon.lab 2>/dev/null | openssl x509 -noout -subject
```

```text
subject=CN = TRAEFIK DEFAULT CERT
```

Pour un nom qu'il ne connaît pas, Traefik sert son propre certificat,
`TRAEFIK DEFAULT CERT`. Si un client voit ce nom, Traefik n'a pas trouvé de
certificat pour l'hôte demandé : Secret absent, mal nommé, ou hôte absent de
la section `tls` de l'Ingress.

Appelez le site avec curl, en lui donnant votre certificat comme autorité de
confiance (`--cacert`) :

```bash
curl -sS -o /dev/null -w '%{http_code}\n' --cacert ~/essai-tls/cn.crt --resolve kiosque.salon.lab:30443:127.0.0.1 "https://kiosque.salon.lab:30443/"; echo "curl : code $?"
```

```text
200
curl : code 0
```

curl accepte ce certificat sans SAN : il retombe sur le CN. Les navigateurs
actuels et les programmes écrits en Go refusent un tel certificat. Un test au
curl ne suffit donc pas : créez toujours vos certificats avec un SAN, comme à
l'exercice 3.

## 🔑 Exercice 2 : une clé qui ne va pas avec le certificat

Fabriquez un certificat avec SAN, puis une autre clé, sans rapport. Essayez de
ranger ce certificat avec la mauvaise clé :

```bash
cd ~/essai-tls && openssl req -x509 -newkey rsa:2048 -nodes -days 30 -subj '/CN=kiosque.salon.lab' -addext 'subjectAltName=DNS:kiosque.salon.lab' -keyout san.key -out san.crt 2>/dev/null && openssl genrsa -out autre.key 2048 2>/dev/null; kubectl create secret tls kiosque-melange -n essai-tls --cert=$HOME/essai-tls/san.crt --key=$HOME/essai-tls/autre.key
```

```text
error: tls: private key does not match public key
```

`kubectl create secret tls` refuse : la clé privée ne correspond pas à la clé
publique du certificat. Ce contrôle est fait par cette commande. Un Secret
écrit en YAML et envoyé avec `kubectl apply` n'y passe pas, et l'erreur ne se
verrait alors qu'au moment où Traefik essaie de l'utiliser.

## 🔄 Exercice 3 : remplacer le certificat à chaud

Remplacez le contenu du Secret `kiosque-cn` par le certificat avec SAN et sa
bonne clé. `--dry-run=client -o yaml` fabrique le Secret sans l'envoyer, et
`kubectl replace` remplace l'ancien :

```bash
kubectl create secret tls kiosque-cn -n essai-tls --cert=$HOME/essai-tls/san.crt --key=$HOME/essai-tls/san.key --dry-run=client -o yaml | kubectl replace -f -; sleep 5; curl -sS -o /dev/null -w '%{http_code}\n' --cacert ~/essai-tls/san.crt --resolve kiosque.salon.lab:30443:127.0.0.1 https://kiosque.salon.lab:30443/
```

```text
secret/kiosque-cn replaced
200
```

Traefik a repris le nouveau certificat en moins de 5 secondes, sans
redémarrer et sans toucher à l'Ingress. C'est ainsi qu'on renouvelle un
certificat. Lisez ses dates de validité, directement sur la connexion :

```bash
echo | openssl s_client -connect 127.0.0.1:30443 -servername kiosque.salon.lab 2>/dev/null | openssl x509 -noout -dates
```

```text
notBefore=Nov 21 00:03:53 2026 GMT
notAfter=Dec 21 00:03:53 2026 GMT
```

`notAfter` est la date d'expiration, 30 jours après la création
(`-days 30`). Lire les dates sur ce que sert le contrôleur, et non sur le
fichier, prouve que c'est bien le nouveau certificat qui est en service.

## 🃏 Exercice 4 : un certificat pour tous les hôtes d'un domaine

Fabriquez un certificat wildcard, valable pour `*.salon.lab`, et rangez-le
dans un nouveau Secret :

```bash
cd ~/essai-tls && openssl req -x509 -newkey rsa:2048 -nodes -days 30 -subj '/CN=*.salon.lab' -addext 'subjectAltName=DNS:*.salon.lab' -keyout joker.key -out joker.crt 2>/dev/null; kubectl create secret tls salon-joker -n essai-tls --cert=$HOME/essai-tls/joker.crt --key=$HOME/essai-tls/joker.key
```

```text
secret/salon-joker created
```

Faites-le servir pour trois hôtes : `kiosque.salon.lab`, `accueil.salon.lab`
et `a.b.salon.lab`, avec une règle pour chacun :

```bash
kubectl patch ingress kiosque -n essai-tls --type json -p '[{"op":"replace","path":"/spec/tls","value":[{"hosts":["kiosque.salon.lab","accueil.salon.lab","a.b.salon.lab"],"secretName":"salon-joker"}]},{"op":"add","path":"/spec/rules/-","value":{"host":"accueil.salon.lab","http":{"paths":[{"path":"/","pathType":"Prefix","backend":{"service":{"name":"kiosque","port":{"number":80}}}}]}}},{"op":"add","path":"/spec/rules/-","value":{"host":"a.b.salon.lab","http":{"paths":[{"path":"/","pathType":"Prefix","backend":{"service":{"name":"kiosque","port":{"number":80}}}}]}}}]'; sleep 5
```

```text
ingress.networking.k8s.io/kiosque patched
```

Appelez les deux premiers :

```bash
for h in kiosque.salon.lab accueil.salon.lab; do printf '%s -> ' $h; curl -sS -o /dev/null -w '%{http_code}\n' --cacert ~/essai-tls/joker.crt --resolve $h:30443:127.0.0.1 "https://$h:30443/"; done
```

```text
kiosque.salon.lab -> 200
accueil.salon.lab -> 200
```

Un seul certificat couvre les deux hôtes. Regardez maintenant celui que reçoit
`a.b.salon.lab` :

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

Le joker `*` ne couvre qu'un seul niveau : `a.salon.lab`, mais pas
`a.b.salon.lab`. Traefik ne trouve donc aucun certificat pour ce nom, malgré
la section `tls` de l'Ingress, et sert le sien. curl le refuse (code 60).
Pour un sous-domaine à deux niveaux, il faut un SAN de plus dans le
certificat.

## ↪️ Exercice 5 : renvoyer le HTTP vers le HTTPS

Pour l'instant, le site répond aussi en HTTP clair :

```bash
curl -s -o /dev/null -w '%{http_code}\n' --resolve kiosque.salon.lab:30080:127.0.0.1 http://kiosque.salon.lab:30080/
```

```text
200
```

L'Ingress standard ne sait pas demander une redirection. Avec Traefik, elle
passe par une ressource propre à Traefik, un Middleware, qu'on rattache à
l'Ingress par une annotation. Le nom à donner dans l'annotation est
`<namespace>-<nom>@kubernetescrd` :

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

Rappelez le site en HTTP :

```bash
curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' --resolve kiosque.salon.lab:30080:127.0.0.1 http://kiosque.salon.lab:30080/
```

```text
301 https://kiosque.salon.lab:30443/
```

`301` et l'adresse HTTPS : le client est renvoyé vers le port 30443.
`permanent: true` donne un 301, que les navigateurs gardent en mémoire. Sans
lui, la redirection est temporaire, ce qui est plus prudent pendant les
essais.

## 🧹 Nettoyage

Supprimez le namespace d'essai et le répertoire des certificats :

```bash
kubectl delete namespace essai-tls; rm -rf ~/essai-tls
```

```text
namespace "essai-tls" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-ingress-tls
dsoxlab check cks-ingress-tls
```

```text
╭─── Résultat : cks-ingress-tls ────╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests  │
╰───────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un site à servir en HTTPS avec son propre
certificat, et la preuve que c'est bien le vôtre que le contrôleur présente.

```bash
dsoxlab run cks-ingress-tls
dsoxlab challenge cks-ingress-tls
```
