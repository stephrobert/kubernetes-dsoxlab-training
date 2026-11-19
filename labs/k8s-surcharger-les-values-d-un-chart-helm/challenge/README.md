# Challenge: Override the values of a Helm chart without falling into the typing trap

## The situation

In the namespace **`helm-values`**, the release **`catalogue`** deploys the
**podinfo 6.16.0** chart. The operations team set two settings on it with
`--set`: **three replicas** and the interface colour **`#ff6b00`**.

You are asked to upgrade it to **6.17.0** and to set the interface message to
**`2026`**, the catalogue year.

You are on the control plane, with `kubectl` and `helm` 4.3.2. The `podinfo`
repository is already declared. Work in **`~/catalogue`** if you write values
files.

## What you must achieve

1. The release values carry **`ui.message`** equal to the **string** `"2026"`,
   not the integer 2026.
2. The release runs **podinfo 6.17.0**, deployed, and keeps the operations
   settings: **three replicas** and the colour **`#ff6b00`**.
3. podinfo **answers** the message `2026`.

## Landmarks

`helm get values` shows the values a release received; `--all` adds the chart
defaults. `-f` reads a values file, `--set` sets a value on the command line.
`--set` guesses the type: a number becomes an integer, and `true`, `false` and
`null` become booleans or nothing. `--set-string` keeps a string. A
`helm upgrade` without values starts again from the chart defaults;
`--reuse-values` takes those of the previous revision.

## How you will know it works

The tests read the values and the status of the release, then query the
application.

```bash
dsoxlab check k8s-surcharger-les-values-d-un-chart-helm
```
