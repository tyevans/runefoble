---
id: '0961'
title: Daily PostgreSQL Backup to Storage Outside the Cluster, and a Tested Restore
status: Refined
created: 2026-11-19
dependencies:
- '0959'
governing_adrs:
- ADR-0005
- ADR-0015
governing_prds:
- PRD-0025
governing_stories: []
target_bc: core
target_release: 1.0.0
---

# TASK-0961: Daily PostgreSQL Backup to Storage Outside the Cluster, and a Tested Restore

## Status

Refined. Release One hosting slice 9 (PRD-0025, outcomes 5 and 8: a restore test recovers a campaign from a backup, and daily backups exist).

Scope: this record covers PostgreSQL backup and restore only. The list slug still names Redis authentication and the Loki and Grafana volumes. Those two items are not in this slice. The list owner must give them a new id (see the Summary).

## Summary

Add a daily PostgreSQL dump that uploads to an S3-compatible bucket outside the cluster. Add a restore Job that is off by default. Add a restore test that recovers a campaign in a fresh release. Redis authentication, Loki and Grafana persistence, and Silo object backup stay out of this slice.

## Problem Statement

- `deployments/helm/runefoble/templates/` has no CronJob (search found none). No backup of any kind runs.
- `values.yaml:136-147` defines one PostgreSQL StatefulSet with a 5 Gi claim. The claim holds every event store, Zitadel, SpiceDB, and OpenPanel data. Deleting the claim deletes the data (`values.yaml:142-144`).
- `templates/postgres.yaml:27` creates the databases `zitadel`, `spicedb`, and `openpanel` at start. The event-store database is `runefoble`.
- `values.yaml:166-188` (Silo) stores objects in the same cluster. A backup there shares the failure domain. The PRD states that backups need storage outside the cluster (PRD-0025, "What it costs at scale").
- `templates/redis.yaml:23` runs Redis with no password. Out of scope here.
- `values.yaml:23-24` sets the database password default `runefoble_dev_password` (DEV-ONLY). Record 0959 moves it to a Secret.

## Documentation & Architecture Review

- ADR-0015 (f): the PostgreSQL event store is the source of truth in deployed environments. A backup of PostgreSQL is a backup of the event store.
- ADR-0005: the backup is a chart object (CronJob) so that it deploys with the release.
- `docs/reference/platform-services.md`: lists PostgreSQL. Add the backup and restore state.
- New how-to content for the restore steps belongs to the runbook (0965). This record adds a reference section to `docs/reference/hosted-profile.md`.

## Product & User Story References

- PRD-0025, Checkable Outcome 5 (a backup restore test recovers a campaign) and "What good looks like" 8 (daily backups).
- PRD-0025, "What it costs at scale": daily backup needs storage outside the cluster.
- No user story. This is platform work.

## Detailed Specification & Implementation Plan

1. Backup CronJob `postgres-backup` (new template `templates/postgres-backup.yaml`). It renders when `backup.enabled` is `true`. The hosted example sets it. Local defaults keep it off.
   - Values (read with `default`, set in the hosted example): `backup.schedule` (default `"17 2 * * *"`, daily), `backup.endpoint` (HTTPS S3 endpoint outside the cluster, input D8), `backup.bucket`, `backup.credentialsSecret` (keys `access-key`, `secret-key`, record 0959), `backup.image` (an S3 client image pinned by digest, input D8), `backup.retentionDays` (documentation only; see 4), `backup.encryption` (input D8).
   - The Job runs `pg_dumpall` from the pinned PostgreSQL image (`postgres.image`), compresses the output, encrypts it when `backup.encryption` is set, and uploads it to `backup.bucket` under a key with the UTC date.
   - Set `concurrencyPolicy: Forbid`, a `backoffLimit`, and a `successfulJobsHistoryLimit`. The Job never prints the credentials.
2. Guard (0955): the hosted render fails when `backup.enabled` is not `true`, or when `backup.endpoint` does not start with `https://`.
3. Restore Job `postgres-restore` (new template). It renders only when `restore.enabled` is `true`. The default is off. It downloads one named object, decrypts it when needed, and runs `psql` into the database that it names. The runbook states that the restore runs only into an empty database or a fresh release.
4. Retention. The bucket lifecycle rule enforces the retention period (input D8). The Job does not delete old objects. Document the lifecycle rule in the runbook (0965).
5. Keep local rendering unchanged. The backup and restore templates render nothing when their flags are off.

Rules for this record:
- The backup credentials come only from the Secret (0959). They never appear in a values file.
- The restore Job never runs in the release by default.

### Inputs (user decisions)

- D8: backup target (S3-compatible endpoint, bucket, region), owner of the bucket and its keys, retention period, encryption on or off, and the encryption key source (a Secret key, recorded in 0959).
- D8b: the policy for the `runefoble-recordings` bucket (player audio). This record does not back up Silo objects. Decide whether the recordings bucket needs a backup and its own record.

## Frontdoor Blackbox Test Plan

Render tests in `tests/test_blackbox_helm_postgres_backup.py`:
- Hosted render: one CronJob `postgres-backup` with the schedule value and the endpoint value. No credential literal appears in the Job spec.
- Hosted render with `restore.enabled=false` (default): no `postgres-restore` Job.
- Guard: `backup.enabled=false` in the hosted copy fails the render. An `http://` endpoint fails the render.
- Local default render: no backup CronJob.

Live restore test (`tests/test_blackbox_postgres_backup_restore.py`, marked `@requires-kind`, runs in the 0964 smoke job):
1. Install release A on Kind with backup enabled. The S3 endpoint is the in-cluster Silo service. This is a test value only, and it stands in for the external store.
2. Through the public gateway API only, create a campaign and an invite (UI or REST, no database write).
3. Start the backup with `kubectl create job --from=cronjob/postgres-backup`. This is the operator action in the runbook.
4. Install release B in a new namespace, with restore enabled and the object name from step 3.
5. Through the public gateway API of release B, sign in as the same user, and check that the campaign is listed. The test asserts only public responses.

## Definition of Done

- Render tests pass. The live restore test passes in the 0964 smoke job.
- The restore steps and the lifecycle rule are in the runbook (0965).
- `docs/reference/hosted-profile.md` lists the backup and restore values.
- D8 and D8b are recorded.
- The Redis authentication and Loki and Grafana volume items are recorded as separate work by the list owner.
- `CHANGELOG.md` `[Unreleased]` entry. Recorded at merge.

## Audit Provenance

- Severity: high (no backup exists; a PVC loss deletes all event stores).
- Source audits: `.audit/research/r1-hosting.md`, sections 5 and 11 (D8). Lines were checked against `main` at `33885a70`.
