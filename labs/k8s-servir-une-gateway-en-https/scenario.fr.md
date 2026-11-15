# Servir une Gateway d'Istio en HTTPS avec un certificat de cert-manager

## La situation

Le cluster kubeadm compte désormais **trois nœuds** : le control plane et deux
workers. Istio 1.32 y tourne en **mode ambient**, et la Gateway API v1.6.1 est
installée : la GatewayClass **`istio`** est prête à déployer un Envoy pour
chaque Gateway que vous déclarez.

cert-manager v1.21.3 est installé lui aussi, avec une autorité de
certification interne : le ClusterIssuer **`ca-formation`** signe des
certificats pour tout le cluster. Son propre certificat est dans le Secret
`ca-formation` du namespace `cert-manager`.

Dans le namespace **`vitrine`**, l'application `vitrine` répond en HTTP clair
derrière le Service `vitrine` (port 80). L'équipe veut la servir en HTTPS sous
le nom **`vitrine.formation.test`**, par une Gateway, avec un certificat que
cert-manager émet et renouvelle.

Le cluster n'a **aucun répartiteur de charge**. Vous êtes sur le control plane,
avec `kubectl` configuré, en root.

## Ce que vous devez obtenir

1. Un **Certificate** de cert-manager pour `vitrine.formation.test`, émis par
   le ClusterIssuer `ca-formation`, est **prêt** dans le namespace `vitrine`.
2. Une **Gateway** de classe `istio` dans `vitrine` porte un **listener HTTPS
   sur le port 443** qui termine le TLS avec le Secret de ce certificat, et le
   cluster la déclare **Programmed**.
3. Le listener **présente** le certificat que cert-manager a rangé, pour le nom
   `vitrine.formation.test`.
4. Le certificat présenté est **émis par la CA interne**, et sa chaîne se
   vérifie contre elle.
5. Un client HTTPS qui ne fait confiance **qu'à** la CA interne atteint
   l'application `vitrine` par la Gateway.

## La méthode, pas à pas

**Demander le certificat là où vit la Gateway.** Un listener lit son
certificat dans un Secret de **son propre namespace**. Un autre namespace n'est
possible qu'avec un `ReferenceGrant`, dont ce lab n'a pas besoin. Le
`Certificate` va donc dans `vitrine` : `dnsNames` porte le nom, `issuerRef`
vise le **ClusterIssuer** `ca-formation` (le kind compte : aucun `Issuer` de ce
nom n'existe), et `secretName` nomme le Secret que cert-manager écrira.
`kubectl get certificate -n vitrine` doit afficher `READY True`.

**Déclarer la Gateway.** `gatewayClassName: istio`, un listener avec
`protocol: HTTPS`, `port: 443`, `hostname: vitrine.formation.test`, et un bloc
`tls` en `mode: Terminate` dont `certificateRefs` nomme le Secret. Istio crée
pour elle un Deployment et un Service dans le même namespace.

**Penser à l'adresse.** Par défaut, Istio demande un Service de type
`LoadBalancer`. Sur un cluster sans répartiteur, ce Service n'obtient jamais
d'adresse, et la Gateway reste **non Programmed** : `kubectl describe gateway`
dit pourquoi. L'annotation `networking.istio.io/service-type: ClusterIP` sur la
Gateway demande une adresse interne à la place.

**Attacher une route.** Une `HTTPRoute` dans `vitrine`, avec `parentRefs` vers
la Gateway (et `sectionName` vers le listener pour être explicite), `hostnames`
avec le nom, et un `backendRef` vers le Service `vitrine`, port 80. Sans elle,
la Gateway répond 404.

**Vérifier comme un client.** Prenez l'adresse ClusterIP du Service qu'Istio a
créé (`kubectl get svc -n vitrine -l
gateway.networking.k8s.io/gateway-name=<nom>`). `openssl s_client -connect
<ip>:443 -servername vitrine.formation.test` montre le certificat présenté et
son émetteur. Extrayez la CA avec `kubectl get secret ca-formation -n
cert-manager -o jsonpath='{.data.tls\.crt}' | base64 -d > ca.crt`, puis
`curl --cacert ca.crt --resolve vitrine.formation.test:443:<ip>
https://vitrine.formation.test/` doit répondre `vitrine`, sans `-k`.

## Comment vous saurez que ça marche

Les tests cherchent votre Certificate et lisent s'il est prêt, lisent les
conditions de la Gateway et de son listener, puis ouvrent une vraie connexion
TLS vers le listener : ils comparent le certificat présenté au Secret écrit par
cert-manager, le vérifient contre la CA interne, et envoient une requête HTTPS
qui doit atteindre l'application.

```bash
dsoxlab check k8s-servir-une-gateway-en-https
```
