# Security Policy

**Language:** [English](./SECURITY.md) · [Français](./SECURITY.fr.md)

## Supported versions

`kubernetes-dsoxlab-training` is under active development. Security fixes are
applied to the latest version of the `main` branch.

| Version | Supported |
| --- | --- |
| latest (`main`) | yes |
| older | no |

## Reporting a vulnerability

**Do not open a public issue for a security vulnerability.**

If you believe you have found a vulnerability, report it privately:

- Preferably: open a
  [private security advisory](https://github.com/stephrobert/kubernetes-dsoxlab-training/security/advisories/new)
  on GitHub.
- Otherwise, use the contact details published on
  <https://blog.stephane-robert.info>.

Please include:

- a description of the vulnerability and its impact,
- the steps to reproduce it (command, environment, `dsoxlab --version`),
- any relevant log or proof of concept.

We will keep you posted on the progress of the fix, and credit you in the
release notes if you wish.

## Disclosure policy

We practise coordinated disclosure and commit to the following timelines,
counted from the moment we receive your report:

| Step | Target |
| --- | --- |
| Acknowledgement of your report | within **48 hours** |
| Initial assessment and severity triage | within **5 days** |
| Fix published, or a written remediation plan | within **30 days** |
| Public disclosure of the vulnerability | within **90 days** |

We publish the advisory as soon as a fix is available, or at the **90 day**
mark at the latest, whichever comes first. If a vulnerability is being actively
exploited, we may disclose earlier to protect users. If a complex fix needs more
time, we tell you before the deadline and agree a new date with you, rather than
letting it lapse in silence.

## Scope

This repository ships **lab content** executed by the external `dsoxlab` CLI:
scenarios, tests, setup and cleanup playbooks, a kubeadm cluster foundation, and
a public SSH key.

**In** scope:

- dangerous or malicious lab material: a `setup.yaml`, a `cleanup.yaml`, a
  fixture script or a test that does something other than what it announces;
- a leaked secret, or a private key committed by mistake;
- a flaw in the `shared/` foundation: it is included by every lab and runs as
  `root` on both machines.

One remark is specific to this catalogue: **several labs deliberately install a
broken or weakened state**, because that is their subject. A troubleshooting lab
breaks the kubelet, an AppArmor lab loads a profile, an RBAC lab creates an
account that is deliberately under-privileged. That is not a vulnerability: it
is the substance of the exercise, and every `cleanup.yaml` undoes what its lab
set up. These labs are built for **disposable machines**, provisioned by
`dsoxlab provision` and destroyed by `dsoxlab destroy`, never for a machine that
serves another purpose.

**Out** of scope: vulnerabilities in the `dsoxlab` engine itself, which belong in
[its own repository](https://github.com/stephrobert/dsoxlab), and issues in
third-party dependencies, to be reported to their respective projects.
