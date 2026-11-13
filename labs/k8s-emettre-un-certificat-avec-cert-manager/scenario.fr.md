# Émettre des certificats avec cert-manager et une CA interne

## La situation

L'équipe veut des certificats TLS pour ses services internes, émis et
renouvelés sans intervention. **cert-manager** est installé dans le cluster.
Pas d'ACME public ici : le cluster n'est pas joignable depuis Internet. Les
certificats viendront d'une **CA interne**, qu'il faut d'abord construire.

Un collègue a déjà déclaré le certificat **`api-tls`**, dans le namespace
**`atelier-tls`** : il reste « not ready ».

Vous êtes sur **`k8s-cp.lab`**, avec `kubectl` configuré.

## Ce que vous devez obtenir

Dans le namespace **`atelier-tls`** :

1. Un Issuer **auto-signé** nommé **`auto-signe`**, prêt.
2. Une **CA interne** : un Certificate **`ca-interne`**, certificat
   d'autorité, émis par `auto-signe`, dans le Secret `ca-interne` ; et un
   Issuer **`ca-interne`** qui signe avec ce Secret, prêt.
3. Un Certificate **`vitrine-tls`** pour le nom **`vitrine.atelier-tls.svc`**,
   émis par la CA interne, prêt.
4. Le Certificate **`api-tls`** **réparé** : prêt, et émis par la CA interne.

## Les repères utiles

- Un `Issuer` vit dans un namespace, un `ClusterIssuer` dans tout le cluster.
  Un Issuer `selfSigned` signe chaque certificat avec sa propre clé.
- Un Certificate avec `isCA: true` produit un certificat d'autorité. Un Issuer
  de type `ca` signe ensuite avec le Secret qui le contient.
- Un Certificate « not ready » se diagnostique de haut en bas : `kubectl
  describe certificate`, puis la `CertificateRequest` qu'il a créée, puis les
  événements du namespace.
- `kubectl get secret <nom> -o jsonpath='{.data.tls\.crt}' | base64 -d |
  openssl x509 -noout -subject -issuer -dates` lit le certificat émis.

## Comment vous saurez que c'est bon

Les tests lisent les émetteurs et les certificats, puis vérifient chaque chaîne
avec `openssl verify` contre la CA interne : un certificat prêt mais signé par
le mauvais émetteur ne passe pas.

```bash
dsoxlab check k8s-emettre-un-certificat-avec-cert-manager
```
