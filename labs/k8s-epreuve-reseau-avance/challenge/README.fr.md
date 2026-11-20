# Challenge : Épreuve du niveau 6 : exposer et protéger un service sur Cilium

## La situation

La boutique déménage sa vitrine sur le cluster Cilium des hôtes `net-*` :
`net-cp.lab`, `net-w1.lab`, `net-w2.lab`. Cilium 1.20.5 y remplace kube-proxy.
Personne n'y a touché depuis l'installation : pas de Gateway, pas de politique
réseau, pas de chiffrement, et le cluster n'a **aucun répartiteur de charge**.

Dans l'espace **`boutique`** :

- la **vitrine** répond en HTTP derrière le Service **`vitrine`** (port 80) ;
- **`caisse`** est son client légitime ;
- **`publicite`**, un traceur publicitaire, la joint aussi, et n'a rien à y
  faire ;
- **`relance`**, un robot de relance, porte les mêmes étiquettes que
  `caisse` et appelle la vitrine en boucle. En plus de la lire, il envoie une
  requête qu'une vitrine en lecture seule doit refuser. Laquelle, personne ne
  s'en souvient.

Le certificat de `vitrine.formation.test` est prêt dans le Secret
**`vitrine-tls`**. Il est signé par l'autorité propre à la boutique, publiée
dans la ConfigMap **`ca-boutique`**.

Vous travaillez sur `net-cp.lab`, avec `kubectl` et `helm`. La Gateway API
que Cilium 1.20.5 prend en charge est la **v1.6.3**. Pour les adresses des
services exposés, l'équipe réseau vous confie **`172.31.0.0/28`**.

## Ce que vous devez obtenir

1. Un **Gateway** servi par Cilium dans `boutique` est prêt et a une adresse.
2. Il sert `https://vitrine.formation.test/` avec le certificat de
   `vitrine-tls`.
3. Ce nom mène à la vitrine, et seulement ce nom.
4. Par le Gateway, la vitrine se **lit** (GET), et une tentative
   d'**écriture** (POST) est **refusée en 403**.
5. `caisse` lit sans écrire ; `publicite` ne joint plus du tout la vitrine.
6. Le trafic entre nœuds est **chiffré en WireGuard**.
7. La ConfigMap **`diagnostic`** de `boutique` nomme la requête que votre
   protection refuse à `relance` : clé **`methode`** (par exemple `DELETE`) et
   clé **`chemin`** (par exemple `/panier`).

## Règles

Ni pas-à-pas ni indice : la formation vous a donné les outils. L'épreuve est
réussie à **70 %**. Deux
exigences ne se compensent pas par les autres : la lecture seule par le Gateway
(4) et le chiffrement (6).

```bash
dsoxlab check k8s-epreuve-reseau-avance
```
