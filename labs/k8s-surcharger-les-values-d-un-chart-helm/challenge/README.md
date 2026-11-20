# Challenge: Override the values of a Helm chart without falling into the type trap

## 📍 The situation

In the **`helm-values`** namespace, the **`catalogue`** release deploys the
**podinfo 6.16.0** chart. The operations team set two settings on it with
`--set`: **three replicas** and the interface colour **`#ff6b00`**.

You are asked to upgrade it to **6.17.0** and to set the interface message to
**`2026`**, the year of the catalogue.

You are on the control plane, with `kubectl` and `helm` 4.3.2. The `podinfo`
repository is already declared. Work in **`~/catalogue`** if you write values
files.

## 🎯 What you must obtain

1. The values of the release hold **`ui.message`** equal to the **string**
   `"2026"`, not the integer 2026.
2. The release is on **podinfo 6.17.0**, deployed, its Pods run the
   **6.17.0** image, and it keeps the settings of the operations team:
   **three replicas** and the colour **`#ff6b00`**.
3. podinfo **answers** with the message `2026`.

## 🧭 Useful landmarks

`helm get values` shows the values a release received. `--all` adds the
chart's defaults. `-f` reads a values file, `--set` sets a value on the command
line. `--set` guesses the type: a number becomes an integer, and `true`,
`false` and `null` become booleans or nothing. `--set-string` keeps a string.
As soon as a `helm upgrade` receives values, it starts again from the chart's
defaults plus those values only. `--reuse-values` takes back all those of the
previous revision, including the default values of the previous version of
the chart.

## ✅ How you will know it works

The tests read the values and the status of the release, then query the
application.

```bash
dsoxlab check k8s-surcharger-les-values-d-un-chart-helm
```
