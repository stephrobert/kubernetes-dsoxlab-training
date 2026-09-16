# Exiger le mTLS dans un maillage, et le prouver par un client qui reste dehors

Lab **CKS**, domaine *Monitoring, Logging and Runtime Security* (20 % de
l'épreuve), chiffrement du trafic entre Pods.

Le lab n'enseigne pas à installer un maillage : le setup le pose. Ce qu'il
mesure, c'est l'**exigence**, et le fait qu'elle agisse. Un maillage installé
sans PeerAuthentication est en mode PERMISSIVE : il accepte le chiffré comme
le clair, et ne protège de rien. C'est l'écart que ce lab rend visible.

La preuve ne tient à aucune chaîne de caractères : le test attend que le Pod
sans sidecar soit bloqué, puis vérifie que le Pod maillé passe encore. Les
deux mesures sont dans le **même** test, délibérément. « Le client maillé
passe » est déjà vrai AVANT le travail : isolée, cette assertion ferait un
test vert qui ne mesure rien.

Mesuré le 2026-09-16, sur ce socle :

- istiod en profil `minimal` consomme environ **194 Mo**, ce qui tient
  largement dans les 4 Go du control plane. Le profil par défaut ajoute des
  passerelles dont ce lab n'a aucun usage ;
- sans PeerAuthentication, `client-nu` obtient la page ; avec STRICT, sa
  connexion est refusée par le sidecar du service, tandis que `client-maille`
  continue d'être servi.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 30 minutes |
| Leçon jumelée | [Chiffrer le trafic entre Pods avec mTLS](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/mtls-pod-to-pod/) |

```bash
dsoxlab run   cks-istio-mtls-lockdown
dsoxlab check cks-istio-mtls-lockdown
```

Le `cleanup.yaml` désinstalle Istio en entier avec `istioctl uninstall
--purge`. Les CRD et les webhooks sont des objets de **cluster** : ils
survivraient aux namespaces, et le validateur les compterait comme une trace
laissée au lab suivant.

**Le purge ne suffit pourtant pas**, et c'est le validateur qui l'a trouvé :
istiod pousse son certificat de CA racine dans un ConfigMap
`istio-ca-root-cert` de **chaque** namespace, `kube-system` compris, et
`--purge` laisse ces copies derrière lui. Comme chaque installation génère un
nouveau CA, le ConfigMap n'est pas seulement laissé, son contenu **change**
d'un passage à l'autre. Le premier passage a rendu ROUGE sur exactement cela :

```
kube-system configmap/istio-ca-root-cert : 'f6df77835939' devenu '0d2005cac2d8'
```

Le cleanup énumère donc les namespaces pour les retirer un à un, `kubectl
delete` n'acceptant pas `--all-namespaces`.

Écrit le 2026-09-16, puis validé par `scripts/valider-labs.py` : 0 avant le
travail, 100 après la solution du formateur, rejouable et sans trace.
