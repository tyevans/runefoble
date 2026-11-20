# Hosted values profile

This page lists the hosted keys, the check that guards each key, and the placeholder marker.
The profile is a values file. It is not a second chart. Source: `deployments/helm/runefoble/values.hosted.example.yaml`
and `deployments/helm/runefoble/templates/hosted-guard.yaml`.

## Use the profile

1. Copy `deployments/helm/runefoble/values.hosted.example.yaml` to a file outside the repository.
2. Replace every `REPLACE-ME` with your value.
3. Create the Secret named in `credentials.existingSecret`. It holds every key in [`hosted-secrets.md`](hosted-secrets.md).
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
| `credentials.existingSecret` | `runefoble-hosted-credentials` | `templates/secret.yaml` fails when it is empty. The chart then renders no credential Secret, so no `DEV-ONLY` value reaches the output. The Secret keys are in [`hosted-secrets.md`](hosted-secrets.md). |
| `services.campaignLore.embeddingApiKeySecret` | `campaign-lore-embedding` | Fails when it is empty or holds `REPLACE-ME`. The chart renders no Secret with this name in a hosted render. The operator creates it with the key `api-key`. |
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
| `swaggerUI.enabled` | `false` | No guard on the key. A Swagger UI path fails the render (see [Development routes](#development-routes-and-the-analytics-decision-d6)). |
| `openpanel.enabled` | `false` | No guard on the key. An OpenPanel path fails the render (see [Development routes](#development-routes-and-the-analytics-decision-d6)). |
| `ingress.hosts[].paths[]` | No `/mail`, `/mailpit`, `/docs`, `/swagger-ui` or `/analytics` path | Fails on those prefixes. Fails on a path whose service is `mailpit`, `swagger-ui` or `openpanel` when that workload is off. |
| `ingress.tls.mode` | `certManager` | Fails unless `certManager` or `existingSecret`. `none` serves HTTP only. |
| `ingress.tls.clusterIssuer` | `REPLACE-ME` | Required with `certManager`. Fails on `REPLACE-ME`. Name of a ClusterIssuer that you install. |
| `ingress.tls.secretName` | `""` | Required with `existingSecret`. Fails on `REPLACE-ME`. Name of a `kubernetes.io/tls` Secret that you create. |
| `ingress.httpsRedirect` | `true` | Fails unless `true`. Plain HTTP answers 301 to HTTPS. See [TLS and HTTP redirect rules](ports-and-endpoints.md#tls-and-http-redirect-rules-hosted). |
| `backup.enabled` | `true` | Fails unless `true`. A hosted release needs the daily backup. Source: `templates/hosted-guard-backup.yaml`. |
| `backup.endpoint` | `https://REPLACE-ME` | Fails unless it starts with `https://`. Fails on `REPLACE-ME`, `localhost`, or a `svc.cluster.local` host. The bucket must sit outside the cluster. |
| `backup.bucket` | `REPLACE-ME` | Fails on `REPLACE-ME`. |
| `backup.credentialsSecret` | `runefoble-backup-credentials` | Fails on `REPLACE-ME`. The Secret holds `access-key` and `secret-key`. See [`hosted-secrets.md`](hosted-secrets.md). |
| `backup.image` | Chainguard MinIO client, pinned by digest | Fails on `REPLACE-ME`. The client copies the dumps. It needs no shell. |
| `restore.objectPrefix` | `""` | Fails on `REPLACE-ME` when `restore.enabled` is `true`. Required when restore is on. |

## PostgreSQL backup and restore (TASK-0961)

The chart runs one backup CronJob, `postgres-backup`, when `backup.enabled` is `true`. The default
is `false`, so the local render holds no backup object. The hosted example turns it on.

| Value | Default | Meaning |
|---|---|---|
| `backup.schedule` | `17 2 * * *` | Cron schedule, in UTC. The Job runs once a day. |
| `backup.endpoint` | none | HTTPS endpoint of an S3-compatible store outside the cluster. |
| `backup.bucket` | none | Bucket. The dumps go under `postgres/<UTC date>/`. |
| `backup.credentialsSecret` | none | Secret with `access-key` and `secret-key`. Add `encryption-passphrase` when encryption is on. |
| `backup.image` | none | S3 client image, pinned by digest. |
| `backup.encryption.enabled` | `false` | When `true`, each dump is encrypted with AES-256-CBC (PBKDF2). The key is `encryption-passphrase`. |
| `backup.retentionDays` | `30` in the example | Documentation only. The bucket lifecycle rule enforces the period. The chart never deletes an object. |

Each run makes one custom-format `pg_dump` for each database that accepts connections. The dump
reads the `postgres` service and the `postgres-password` key. The Job ends by it logging
`backup-object postgres/<date>`. That prefix names the run. The `concurrencyPolicy` is `Forbid`.

Start a run on demand with `kubectl create job --from=cronjob/postgres-backup <name>`.

### Restore

The restore Job `postgres-restore` renders only when `restore.enabled` is `true`. It is a
post-install hook, so it runs once, for a fresh install. It never runs on upgrade.

1. Set `restore.enabled: true` and `restore.objectPrefix` to the logged prefix, for example `postgres/2026-11-18`.
2. Install the release into an empty namespace, with the same credentials Secret and the same backup values.
3. The Job downloads the prefix. It waits for PostgreSQL, decrypts any `.enc` file, and runs `pg_restore --clean --if-exists` for each dump. The dump name is the database name.
4. Restart the services after the Job completes, so each service reads the restored rows.

A restore replaces the objects of every dumped database. Run it only into a fresh release. The
runbook (TASK-0965) holds the operator steps and the lifecycle rule.

### Lifecycle rule (operator)

Configure a bucket lifecycle rule that expires objects under `postgres/` after `backup.retentionDays`.
The chart does not delete dumps.

## Development routes and the analytics decision (D6)

The guard in `templates/hosted-guard-dev-routes.yaml` fails a staging or production render when:

- an Ingress path equals or sits below `/mail`, `/mailpit`, `/docs`, `/swagger-ui` or `/analytics`; or
- an Ingress path targets `mailpit`, `swagger-ui` or `openpanel`, and that workload is off.

The hosted example serves no development route. Each development workload is off there. A hosted render has no Mailpit, no Swagger UI page and no OpenPanel. Each service still serves `/openapi.json` inside the cluster (AGENTS.md, Hard Invariant 5). A removed route returns 404. The chart adds no substitute page.

Decision D6 (analytics): off by default. OpenPanel is not public and no service needs it. The OpenPanel client (`libs/runefoble_platform/src/runefoble_platform/analytics/client.py`) has no call site in a service. A failed send logs a warning and does not raise, so an off workload cannot block a player action. To turn analytics on for a hosted site, first add authentication in front of the OpenPanel UI, then change the example and the guard in one record.

## Placeholder marker

`REPLACE-ME` marks every value that an operator must set. The guard fails on it in every
hosted key that the table lists. Do not keep the marker in a rendered file.

## Development defaults

`deployments/helm/runefoble/values.yaml` marks the credential defaults as `DEV-ONLY`. Do not
use these values in a hosted render. In a hosted render, the chart does not render them, because
`credentials.existingSecret` names a Secret that you manage.

## Secret decisions

- D5 (Secret source): the operator chooses. A hand-applied Secret or an external-secret operator
  both work. The chart reads only the names. The choice is not a chart decision.
- D5b (narrow the `create` grant): Option A. The chart keeps the namespace-wide `create` grant on
  Secrets, because RBAC cannot limit `create` by name. The residual risk is in
  [`hosted-secrets.md`](hosted-secrets.md), section 5.
