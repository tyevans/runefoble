# Reference: Hosted Secrets

This page lists every Secret key that a hosted release reads. It is the contract between the operator and the chart. The chart reads Secret names and key names. It does not create operator Secrets, and it does not hold their values.

Governing records: ADR-0015 (decisions c and e), PRD-0025 (outcome 8), TASK-0959. The values profile is in [`hosted-profile.md`](hosted-profile.md).

## 1. Rules

- No secret value appears in a values file, a template, or a doc.
- A workload reads each credential with `secretKeyRef`. A plain value never holds a credential.
- No fallback exists. A pod that names a missing Secret or a missing key does not start. Kubernetes reports `CreateContainerConfigError`.
- The local render (`global.environment: local`) renders the Secret `runefoble-credentials` with development defaults. A hosted render (`staging` or `production`) renders no credential Secret. It reads the Secret named in `credentials.existingSecret`.

## 2. Operator Secret source (D5)

The operator chooses how the Secret exists. Two sources work:

- A Secret that the operator applies by hand.
- An external-secret operator that writes a Secret with the same name and the same keys.

The chart does not depend on the choice. D5 is not a chart decision. The operator owns it.

## 3. Secret keys

The table has one row for each key. The column `Secret name` names the source. The value `credentials.existingSecret` means the Secret that the operator names in that value. The value `services.campaignLore.embeddingApiKeySecret` means the Secret that the operator names in that value. The table test (`tests/test_blackbox_helm_hosted_secrets.py`) reads these rows. Keep the names in backticks.

| Secret name | Key | Consumer | Source | Rotation effect | Format rule |
|---|---|---|---|---|---|
| `credentials.existingSecret` | `silo-access-key` | Silo (`MINIO_ROOT_USER`), the silo-buckets Job, and services with `siloCredentials` | Operator-supplied | Restart Silo, the bucket Job, and each reading service. | URL-safe: letters, digits, `-`, `_`, and `.` only. The bucket Job builds `MC_HOST_silo` from this key and `silo-secret-key`. |
| `credentials.existingSecret` | `silo-secret-key` | Silo (`MINIO_ROOT_PASSWORD`), the silo-buckets Job, and services with `siloCredentials` | Operator-supplied | Restart Silo, the bucket Job, and each reading service. | URL-safe, as for `silo-access-key`. |
| `credentials.existingSecret` | `zitadel-masterkey` | Zitadel (`ZITADEL_MASTERKEY`) | Operator-supplied | Do not change after the first start. Zitadel uses this key to encrypt its data. | Exactly 32 bytes. |
| `credentials.existingSecret` | `zitadel-admin-password` | Zitadel (`ZITADEL_FIRSTINSTANCE_ORG_HUMAN_PASSWORD`) | Operator-supplied | Zitadel reads it when it creates the first instance. A later change to this key does not change the stored password. Change the password in Zitadel. | Must meet the Zitadel password policy. |
| `credentials.existingSecret` | `spicedb-preshared-key` | SpiceDB (`SPICEDB_GRPC_PRESHARED_KEY`), the SpiceDB schema Job (`ZED_TOKEN`), and gateway-mcp (`RUNEFOBLE_SPICEDB_PRESHARED_KEY`) | Operator-supplied | Restart SpiceDB, the schema Job, and gateway-mcp together. | Non-empty. Use a random value. |
| `credentials.existingSecret` | `postgres-password` | PostgreSQL (`POSTGRES_PASSWORD`), SpiceDB, OpenPanel, and Zitadel (database users) | Operator-supplied | PostgreSQL reads it when it creates its data directory. A change to this key does not change the password in an existing database. Change the password in PostgreSQL too, then restart each consumer. | Non-empty. Use a random value. |
| `credentials.existingSecret` | `grafana-admin-password` | Grafana (`GF_SECURITY_ADMIN_PASSWORD`) | Operator-supplied | Grafana stores the admin password when it creates its database. A later change to this key does not change the stored password. Change it in Grafana too. | Non-empty. |
| `credentials.existingSecret` | `service-credential` | Every service with `serviceCredential: true`, gateway-mcp, and inference-worker (`RUNEFOBLE_SERVICE_CREDENTIAL`). Sent as the header `X-Runefoble-Service-Credential`. | Operator-supplied | Change every sender and every receiver together, then restart them. | Use at least 32 random bytes, as printable ASCII with no spaces. |
| `credentials.existingSecret` | `smtp-password` | Zitadel SMTP (`ZITADEL_DEFAULTINSTANCE_SMTPCONFIGURATION_SMTP_PASSWORD`), read through `zitadel.smtp.passwordSecretKey`. A hosted render only. | Operator-supplied. The local render holds an empty placeholder that Mailpit does not read. | Restart Zitadel. Zitadel reads the SMTP settings at instance creation (see [`hosted-profile.md`](hosted-profile.md)). | The password that the SMTP provider issues. |
| `services.campaignLore.embeddingApiKeySecret` | `api-key` | campaign-lore (`RUNEFOBLE_EMBEDDING_API_KEY`) | Operator-supplied. The chart renders this Secret only in `local`, with the placeholder `not-required`. | Restart campaign-lore. | Non-empty. The key of the embedding endpoint. |
| `services.inferenceWorker.openaiApiKeySecret.name` | `api-key` | inference-worker (`RUNEFOBLE_WORKER_OPENAI_API_KEY`) | Operator-supplied. The chart renders no Secret with this name. The key name comes from `services.inferenceWorker.openaiApiKeySecret.key`; the example uses `api-key`. | Restart inference-worker. | Non-empty. The key of the model endpoint. |
| `backup.credentialsSecret` | `access-key` | Backup CronJob `postgres-backup` (`MC_HOST_backup`) and restore Job `postgres-restore`, when `restore.enabled` is true | Operator-supplied. The chart renders no Secret with this name. | Restart the next backup run. A change does not affect a running Job. | Access key of the bucket in `backup.bucket`. |
| `backup.credentialsSecret` | `secret-key` | Backup CronJob `postgres-backup` and restore Job `postgres-restore` | Operator-supplied. | As for `access-key`. | Secret key of the bucket in `backup.bucket`. |
| `backup.credentialsSecret` | `encryption-passphrase` | Backup CronJob and restore Job, only when `backup.encryption.enabled` is true | Operator-supplied. | Dumps made with the old passphrase need the old passphrase to restore. Keep it while such dumps exist. | Non-empty. Use a random value. |
| `zitadel-admin` | `pat` | Bootstrap Job (`ZITADEL_ADMIN_PAT`); game-session on `local` only (`RUNEFOBLE_ZITADEL_SERVICE_TOKEN`, invite accounts, ADR-0023). A hosted release sets `zitadel.provisioner.secretName` to an operator Secret with a narrow service user token. | Generated by the pat-publisher sidecar in the Zitadel pod. Do not create it. | The token expires on the date in `zitadel.bootstrap.patExpirationDate`. | Written by the chart. |
| `runefoble-zitadel-client` | `project-id`, `client-id` | Frontend init container, and services that read `RUNEFOBLE_ZITADEL_AUDIENCE` | Generated by the bootstrap Job, a Helm hook that runs before install and upgrade. Do not create it. | The bootstrap Job writes it again on each install and upgrade. | Written by the chart. |

The generated rows name the Secrets by their chart values: `zitadel.bootstrap.adminSecret` and `zitadel.client.secretName`.

## 4. Format rules that the chart cannot check

The chart reads a Secret at run time. It cannot read the content of an operator Secret at render time. The operator must meet these rules:

- Silo keys are URL-safe. A key with `@`, `:`, `/`, `?`, `#`, `%`, or a space can break the `MC_HOST_silo` URL in the bucket Job. The smoke job (TASK-0964) checks the bucket Job on a Kind cluster.
- Keys in the table are case-sensitive. The chart reads them by exact name.

## 5. Residual risk: namespace-wide `create` on Secrets (Option A)

The Zitadel Role (`templates/zitadel.yaml`) and the bootstrap Role (`templates/zitadel-bootstrap.yaml`) grant `create` on all Secrets in the namespace. Kubernetes RBAC cannot limit `create` by name. The writers use server-side apply, and server-side apply needs `create` for a new Secret.

Effect of the grant:

- A process that runs as the Zitadel or bootstrap service account can create a Secret with any name in the namespace.
- It cannot change or read an existing Secret by name. That needs `patch` or `get`. The chart grants those verbs only on the two generated Secrets.

Decision D5b: Option A is in use. The chart keeps `create`. Operators must keep the Runefoble namespace for Runefoble only.

Option B (render the generated Secrets with no data, then grant only `get` and `patch` by name) is not in use. It needs the smoke test (TASK-0964) first.

## 6. Generated Secrets and Helm

The chart renders no object for `zitadel-admin` and `runefoble-zitadel-client`. The writers create them at run time with server-side apply. Helm does not hold their data.

## See also

- [`hosted-profile.md`](hosted-profile.md): the hosted values profile and the render guard.
- [`identity-and-token-contract.md`](identity-and-token-contract.md): the service credential and the token contract.
- [`platform-services.md`](platform-services.md): the development Secret defaults.
