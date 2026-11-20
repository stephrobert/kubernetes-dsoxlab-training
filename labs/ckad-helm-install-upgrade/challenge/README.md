# Challenge: Install, upgrade and roll back with Helm 4

## 📍 The situation

The team ships its web application as a **Helm chart**, in the
**`~/charts/web`** directory of the control plane. The chart is in version
**0.1.0** and deploys nginx 1.30.5. Helm 4 is installed. The **`lab`**
namespace exists, and is empty.

The team is preparing the next version of the chart. It must go to
production, then be taken back out if it causes trouble.

## 🎯 What you must obtain

1. A release **`web`** in `lab`, installed from `~/charts/web` in version
   **0.1.0**, with the chart's default values.
2. The chart moved to version **0.2.0**, and the release **upgraded** with
   that version, **3** replicas and a Pod label **`tier=front`**.
3. The release **back on its revision 1**: the history shows the chart
   `web-0.1.0`, then `web-0.2.0`, then the rollback, which brings back
   `web-0.1.0`.
4. The application **runs** with one replica and **answers**: the Deployment
   is ready, and its Service serves the nginx page.

## 🧭 Useful landmarks

The version of a chart is the `version` field of its `Chart.yaml`. Helm
records it in each revision: it is the `CHART` column of `helm history`.

The chart's `values.yaml` gives the names of the values it accepts, among
them the number of replicas and the labels added to the Pods.

## ✅ How you will know it works

The tests read the history of the release, the values of each revision, the
state of the Deployment and the image the chart renders, then query the
Service.

```bash
dsoxlab check ckad-helm-install-upgrade
```
