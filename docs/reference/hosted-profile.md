# Hosted values profile

This page lists the hosted keys, the check that guards each key, and the placeholder marker.
The profile is a values file. It is not a second chart. Source: `deployments/helm/runefoble/values.hosted.example.yaml`
and `deployments/helm/runefoble/templates/hosted-guard.yaml`.

## Use the profile

1. Copy `deployments/helm/runefoble/values.hosted.example.yaml` to a file outside the repository.
2. Replace every `REPLACE-ME` with your value.
3. Create the Secret named in `credentials.existingSecret`. It holds the keys in `templates/secret.yaml`.
4. Render the chart. Deploy only when the render succeeds:

```sh
helm template runefoble deployments/helm/runefoble -f <your-hosted-values.yaml>
```

`make helm-deploy` is the Kind developer path. It adds `values.local.yaml`. Do not use it for a hosted release.

## Render guard

The guard runs when `global.environment` is `staging` or `production`. It renders no object.
It fails the render on the first key that holds a placeholder or a development default. The
failure message names the key path and the value. The guard does not run for `local`, so the
Kind render does not change.

An unset key that the guard reads also fails the render. The guard never takes a development value for a missing key.

## Hosted keys

| Key | Hosted value in the example | Check |
|---|---|---|
| `global.environment` | `production` | Selects the guard. Use `staging` or `production`. |
| `global.domain` | `REPLACE-ME` | Fails on `REPLACE-ME`, `localhost`, or a `.local` suffix. |
| `credentials.existingSecret` | `runefoble-hosted-credentials` | `templates/secret.yaml` fails when it is empty. The chart then renders no credential Secret, so no `DEV-ONLY` value reaches the output. |
| `ingress.hosts[].host` | `REPLACE-ME` and `auth.REPLACE-ME` | Fails on `REPLACE-ME`, `localhost`, or a `.local` suffix. |
| `zitadel.externalDomain` | `auth.REPLACE-ME` | Fails on `REPLACE-ME`, `localhost`, or a `.local` suffix. |
| `zitadel.externalPort` | `443` | No guard. Must match the public port. |
| `zitadel.externalSecure` | `true` | Fails when `false`. |
| `zitadel.adminEmail` | `admin@REPLACE-ME` | Fails on `REPLACE-ME` or the `@runefoble.local` suffix. |
| `zitadel.bootstrap.patExpirationDate` | `2027-01-01T00:00:00Z` | Fails on `REPLACE-ME` or a `2099` date. Set a short date for your policy. |
| `zitadel.bootstrap.redirectUris` | `https://REPLACE-ME/auth/callback` | Fails on `REPLACE-ME`, `localhost`, `http://`, or a `.local/` path. |
| `zitadel.bootstrap.postLogoutRedirectUris` | `https://REPLACE-ME/` | Same check as `redirectUris`. |
| `zitadel.bootstrap.devMode` | `false` | Fails when `true`. |
| `mailpit.enabled` | `false` | Fails when `true`. Mailpit is a development mail capture. |

## Placeholder marker

`REPLACE-ME` marks every value that an operator must set. The guard fails on it in every
hosted key that the table lists. Do not keep the marker in a rendered file.

## Development defaults

`deployments/helm/runefoble/values.yaml` marks the credential defaults as `DEV-ONLY`. Do not
use these values in a hosted render. In a hosted render, the chart does not render them, because
`credentials.existingSecret` names a Secret that you manage.
