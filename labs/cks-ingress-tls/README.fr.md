# Servir un site en HTTPS avec son propre certificat, et non celui du contrôleur

Lab **CKS**, domaine *Cluster Setup* (15 % de l'épreuve), compétence « Use
Ingress with TLS to secure application access ».

Le contrôleur Ingress est posé par le setup : ce que le lab mesure est la
terminaison TLS, pas l'installation d'un contrôleur.

**Le piège est mesuré, et c'est lui qui fait le lab.** Sans aucune section
TLS, le contrôleur répond déjà **200 en HTTPS**, avec un certificat auto-signé
générique qu'il fabrique au démarrage. Un test qui se contenterait de « le
site répond en HTTPS » serait donc vert **avant** le travail. Ce qui distingue
les deux états est le certificat PRÉSENTÉ, lu sur la connexion elle-même :

| | Certificat servi pour `vitrine.lab` |
|---|---|
| avant | `CN = TRAEFIK DEFAULT CERT` |
| après | `CN = vitrine.lab` |

Aucune lecture de manifeste ne remplacerait cette mesure : un Secret peut
exister, être du bon type, et n'être servi à personne parce que l'Ingress ne
le déclare pas.

**Traefik, et pas ingress-nginx** : ce dernier est archivé depuis le 24 mars
2026, et la leçon du blog a basculé. Chart `traefik/traefik` **41.6.0**,
appVersion v3.7.13, mesuré disponible le 2026-09-16, exposé en NodePort 30080
et 30443 parce qu'un Service LoadBalancer resterait `Pending` sur un cluster
kubeadm sans fournisseur de cloud. Coût mesuré : environ 66 Mo.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 25 minutes |
| Leçon jumelée | [Ingress](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/ingress/) |

```bash
dsoxlab run   cks-ingress-tls
dsoxlab check cks-ingress-tls
```

Le `cleanup.yaml` désinstalle la release **et** supprime les CRD : `helm
uninstall` les laisse derrière lui, délibérément, et ce sont des objets de
cluster que la photographie du validateur verrait apparaître.
