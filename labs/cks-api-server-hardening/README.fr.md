# Fermer le profileur de l'API server, sans fermer l'API

La leçon présente le CIS Benchmark et les réglages qui durcissent un cluster.
Ici, modifier l'API server est le challenge : ce cours ne touche pas à son
manifeste. Il mesure de l'extérieur ce que l'API server et le kubelet laissent
faire, avec des cas que la leçon ne montre pas : ce qu'un client anonyme
obtient de chacun, les réglages d'authentification du kubelet, et les
versions de TLS que les deux acceptent vraiment.

Page associée : [CIS Kubernetes Benchmark : auditer la sécurité de votre cluster](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/cis-benchmark/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-api-server-hardening
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2 et OpenSSL 3.0.13.

## 👤 Exercice 1 : ce qu'un anonyme obtient de l'API server

`curl` sans certificat ni jeton se présente en anonyme. Interrogez trois
chemins de l'API server, et lisez le code de réponse :

```bash
for p in /version /healthz /api/v1/namespaces; do printf '%-22s -> ' $p; curl -sk -o /dev/null -w '%{http_code}\n' "https://127.0.0.1:6443$p"; done
```

```text
/version               -> 200
/healthz               -> 200
/api/v1/namespaces     -> 403
```

`/version` et `/healthz` répondent, la liste des namespaces est refusée
(403). L'anonyme est bien reconnu, mais il n'a presque aucun droit. Ce qui lui
reste vient de cette liaison :

```bash
kubectl get clusterrolebinding system:public-info-viewer -o jsonpath='{.subjects[*].name}{"\n"}'
```

```text
system:authenticated system:unauthenticated
```

Le rôle `system:public-info-viewer` est accordé à tout le monde, connecté ou
non : c'est lui qui ouvre `/version` et `/healthz`.

## 🔒 Exercice 2 : ce qu'un anonyme obtient du kubelet

Le kubelet de chaque nœud expose sa propre API sur le port 10250. Essayez la
même chose sur celui de `k8s-w1.lab` :

```bash
W1=$(kubectl get node k8s-w1.lab -o jsonpath='{.status.addresses[0].address}'); for p in /healthz /pods; do printf 'kubelet %-9s -> ' $p; curl -sk -o /dev/null -w '%{http_code}\n' "https://$W1:10250$p"; done
```

```text
kubelet /healthz  -> 401
kubelet /pods     -> 401
```

401 partout : le kubelet ne reconnaît même pas l'anonyme. Sa configuration le
dit :

```bash
sudo grep -A6 -E '^authentication:|^authorization:' /var/lib/kubelet/config.yaml | head -14
```

```text
authentication:
  anonymous:
    enabled: false
  webhook:
    cacheTTL: 0s
    enabled: true
  x509:
--
authorization:
  mode: Webhook
  webhook:
    cacheAuthorizedTTL: 0s
    cacheUnauthorizedTTL: 0s
cgroupDriver: systemd
```

`anonymous.enabled: false` refuse les clients sans identité. `mode: Webhook`
fait vérifier chaque demande par l'API server, avec les mêmes règles RBAC que
le reste du cluster.

## 🔐 Exercice 3 : les versions de TLS que les serveurs acceptent

Testez d'abord TLS 1.1 sur l'API server avec `openssl` :

```bash
echo | openssl s_client -connect 127.0.0.1:6443 -tls1_1 2>&1 | grep -o -m1 'no protocols available'
```

```text
no protocols available
```

Attention, ce refus vient du **client** : OpenSSL 3 désactive TLS 1.1 de son
côté, sans même contacter le serveur. Pour mesurer le serveur, il faut
rouvrir TLS 1.1 côté client avec `SECLEVEL=0` :

```bash
W1=$(kubectl get node k8s-w1.lab -o jsonpath='{.status.addresses[0].address}'); for cible in $W1:10250 127.0.0.1:6443; do for v in tls1_1 tls1_2 tls1_3; do printf '%-18s %s -> ' $cible $v; echo | openssl s_client -connect $cible -$v -cipher 'DEFAULT@SECLEVEL=0' 2>&1 | grep -o -m1 -E 'New, TLSv1\.[0-9]|alert protocol version'; done; done
```

```text
10.10.50.12:10250  tls1_1 -> alert protocol version
10.10.50.12:10250  tls1_2 -> New, TLSv1.2
10.10.50.12:10250  tls1_3 -> New, TLSv1.3
127.0.0.1:6443     tls1_1 -> alert protocol version
127.0.0.1:6443     tls1_2 -> New, TLSv1.2
127.0.0.1:6443     tls1_3 -> New, TLSv1.3
```

Cette fois, c'est bien le serveur qui refuse TLS 1.1 (`alert protocol
version`), sur le kubelet comme sur l'API server. Les deux acceptent TLS 1.2
et 1.3. Un test de version TLS ne vaut que si le client sait proposer la
version testée.

## 🧹 Nettoyage

Le cours n'a créé aucun objet. Quittez la machine et remettez le lab à zéro.
`dsoxlab reset` rejoue le nettoyage puis la préparation du lab : vous
retrouvez exactement l'état de départ du challenge. Il vous demande de
confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-api-server-hardening
dsoxlab check cks-api-server-hardening
```

```text
╭─ Résultat : cks-api-server-hardening ─╮
│  0 / 100 pts                          │
│  ░░░░░░░░░░░░░░░░░░░░  0/2 tests      │
╰───────────────────────────────────────╯
```

0 sur 2 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : fermer le profileur de l'API server et poser deux
réglages de durcissement, sans casser l'API.

```bash
dsoxlab run cks-api-server-hardening
dsoxlab challenge cks-api-server-hardening
```
