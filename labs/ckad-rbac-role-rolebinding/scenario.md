# Grant read-only access to Pods with RBAC

## The situation

A developer, known to the cluster as **`dev-user`**, has to follow her
deployments in the **`lab`** namespace: see the Pods, and read their logs.
Nothing more. She must neither create nor delete anything, nor see what is
running in the other namespaces.

The namespace exists, with an application inside, the **`journal`** Pod,
which writes to its logs. For now, `dev-user` has no rights at all.

## What you must achieve

1. A Role **`pod-reader`** in `lab`, which allows reading the Pods and their
   logs.

2. A RoleBinding **`read-pods-binding`** in `lab`, which grants that Role to
   the user `dev-user`.

3. `dev-user` can list the Pods of `lab` and read the logs of `journal`.

4. `dev-user` can **not** create a Pod in `lab`, and can **not** list the
   Pods of `default`.

## Useful bearings

`kubectl auth can-i <verb> <resource> -n <namespace> --as <user>` answers
`yes` or `no` without creating anything: it is your measuring instrument,
before as well as after. You can also run a command **as** `dev-user`, with
`--as`.

A Pod's logs are not the Pod: they are a subresource, and it is named
separately.

## How you will know it works

The tests read the Role and the RoleBinding, then they query the API as
`dev-user`, for what must pass as well as for what must be denied.

```bash
dsoxlab check ckad-rbac-role-rolebinding
```
