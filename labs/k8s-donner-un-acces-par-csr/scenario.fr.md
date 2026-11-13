# Donner un accès humain par une CertificateSigningRequest

## La situation

**camille** rejoint l'équipe web. Elle doit pouvoir **lire les Pods** du
namespace **`equipe-web`**, et rien d'autre. Kubernetes n'a pas d'objet
« utilisateur » : un humain s'authentifie par un certificat que le cluster a
signé, et l'API le reconnaît au **CN** de ce certificat.

La règle de l'équipe : la clé de l'autorité de certification ne quitte jamais
le nœud, et personne ne signe à la main avec elle. Le certificat passe par
l'API **CertificateSigningRequest**.

Vous êtes sur **`k8s-cp.lab`**, avec `kubectl` configuré. Le répertoire
**`~/acces`** est vide.

## Ce que vous devez obtenir

1. Une **CertificateSigningRequest** nommée **`camille`**, pour le CN
   `camille`, adressée au signataire des clients de l'API server, pour
   l'authentification d'un client, **approuvée** et **délivrée**.
2. **`~/acces/camille.kubeconfig`** porte le **certificat que l'API a
   délivré** pour cette demande et la clé de camille ; l'API y reconnaît
   **camille**.
3. Avec ce kubeconfig, camille **lit les Pods** d'`equipe-web`.
4. Et **rien de plus** : ni modifier, ni lire les Secrets, ni regarder un autre
   namespace ou les nœuds.

## Les repères utiles

- `openssl genrsa` crée une clé, `openssl req -new -subj "/CN=camille"` une
  demande signée par cette clé.
- Une CertificateSigningRequest porte la demande encodée en base64, un
  `signerName` et des `usages`. `kubectl certificate approve` l'approuve, et le
  certificat délivré apparaît dans son `status.certificate`.
- `kubectl config set-cluster`, `set-credentials` et `set-context`, avec
  `--kubeconfig`, construisent un kubeconfig à part.
- `kubectl auth whoami` et `kubectl auth can-i`, lancés avec ce kubeconfig,
  disent qui l'API voit et ce que cette identité peut faire.

## Comment vous saurez que c'est bon

Les tests lisent la demande camille, comparent le certificat du kubeconfig à
celui que l'API a délivré, puis interrogent l'API sous l'identité de camille.

```bash
dsoxlab check k8s-donner-un-acces-par-csr
```
