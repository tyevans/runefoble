---
id: '0962'
title: Resource Requests, Network Policies, and Pod Security for the Hosted Release
status: Refined
created: 2026-11-19
dependencies:
- '0955'
governing_adrs:
- ADR-0005
- ADR-0015
governing_prds:
- PRD-0025
governing_stories: []
target_bc: core
target_release: 1.0.0
---

# TASK-0962: Resource Requests, Network Policies, and Pod Security for the Hosted Release

## Status

Refined. Release One hosting slice 10 (PRD-0025, outcome 8: private credentials and one hosted cluster).

Scope note for the list owner: this record bundles three slices (requests and limits, network policies, pod security). Split it before it is pulled into active work if the team wants one slice per record.

## Summary

Give every workload resource requests and limits. Add default-deny network policies with explicit allow rules that follow the `consumers` lists. Set a pod and container security context on every workload. Keep one replica for each service. The PRD sets no autoscaling.

## Problem Statement

- `deployments/helm/runefoble/templates/services.yaml:37-47` renders the container block without a `resources` key. Only Redis sets resources (`values.yaml:158-164`, `templates/redis.yaml:26-27`).
- `templates/services.yaml:29` sets `replicas` from the entry, default 1. Every workload is one replica.
- No NetworkPolicy, PodDisruptionBudget, or HorizontalPodAutoscaler exists in the chart (search found none).
- The `consumers` lists (for example `values.yaml:311`, `:323`, `:341`, `:351`, `:377`, `:396`, `:406`, `:464`) define which service calls which. The chart keeps this data but never enforces it.
- `templates/services.yaml:98` renders a pod `securityContext` only for entries that set `podSecurityContext`. Only `voice-agent` sets one (`values.yaml:369-370`, `fsGroup: 10001`).
- The Python image runs as UID 10001 (`deployments/docker/python-service.Dockerfile:54-55`). No read-only root filesystem or capability drop is set.
- `gateway-mcp` keeps state in memory and must stay at one replica (`values.yaml:477-479`).
- The Kind default network plugin may not enforce NetworkPolicy. This must be checked before any live test relies on it.

## Documentation & Architecture Review

- ADR-0015 (e): service calls carry a credential. A network policy adds a second layer. It does not replace the credential.
- ADR-0015 (c): every service verifies its own token. A network policy does not change this.
- `docs/reference/service-client.md` and `docs/reference/ports-and-endpoints.md`: list the service calls. Use them to check the allow rules.
- New reference: `docs/reference/hosted-profile.md` gets the network and security rules. Create the section.

## Product & User Story References

- PRD-0025, "What this does not do": no autoscaling and no abuse controls. Requests and limits cover fair use inside one group. They are not a scale feature.
- No user story. This is platform work.

## Detailed Specification & Implementation Plan

1. Resources:
   - Add a `resources` key to each `services` entry, read with `default`. The template renders it when set. The hosted example sets values from a measured run (input D11).
   - Requests are required. Memory limits are required. CPU limits are optional (document the choice).
   - The local default stays as it is for entries without the key.
2. Network policies (new template `templates/network-policies.yaml`, hosted only):
   - One default-deny ingress policy for the release pods.
   - Allow ingress from the ingress controller namespace (input D2d) to `frontend`, `gateway-api`, `board-state`, and `zitadel`.
   - For every service with `urlEnv`, allow ingress from each pod in its `consumers` list to the service port.
   - Allow ingress from every release pod to the OTel collector port.
   - Allow egress to DNS.
   - Allow egress to the external hosts in the hosted example: the inference endpoint, the embedding endpoint, the STT endpoint, the backup endpoint, and the SMTP host. Use a value list of host and port pairs (input D10, host list). The rule must name the host, not a wide CIDR.
   - Check that the chosen cluster network plugin enforces NetworkPolicy before the live test is trusted.
3. Pod security (default for each workload, set in the template):
   - `runAsNonRoot: true` for the Python services and the frontend. Keep UID 10001 from the Dockerfile.
   - `allowPrivilegeEscalation: false` and `capabilities.drop: [ALL]` for every container.
   - `seccompProfile.type: RuntimeDefault` for every pod.
   - `readOnlyRootFilesystem: true` for the Python services, with an `emptyDir` at `/tmp`. Check each service that writes elsewhere before you turn it on.
   - Third-party images (Zitadel, PostgreSQL, SpiceDB, Redis, Silo, Grafana, Loki, OTel, OpenPanel) have their own users. List each exception in `docs/reference/hosted-profile.md`. Do not set a UID that the image does not support.
4. Replicas stay at one for every service. No HorizontalPodAutoscaler and no PodDisruptionBudget. The PRD sets no autoscaling and one group per cluster.
5. The hosted guard (0955) checks that every Deployment and StatefulSet has a memory request.

Rules for this record:
- Do not change `values.yaml` line count. Put the per-service values in the hosted example.
- No policy allows traffic that a consumer list does not name.

### Inputs (user decisions)

- D2d: ingress controller namespace and pod labels (for the allow rule).
- D10 (host list): the external host and port pairs for the model, embedding, STT, backup, and SMTP endpoints (from 0963 and 0961).
- D11: the scale target for the group (concurrent players and sessions) and the measured resource values. PRD-0025 sets one group. The numbers come from a measured run on the hosted cluster.

## Frontdoor Blackbox Test Plan

Render tests in `tests/test_blackbox_helm_hosted_hardening.py`:
- Hosted render: every Deployment and StatefulSet container has `resources.requests.memory`. Every container has `allowPrivilegeEscalation: false` and `capabilities.drop` `["ALL"]`.
- Hosted render: every pod has `seccompProfile.type` `RuntimeDefault`.
- Hosted render: every Python service runs with `runAsNonRoot: true`. The exceptions list matches `docs/reference/hosted-profile.md`.
- Hosted render: the default-deny policy exists. For each `consumers` pair, one allow rule exists. No allow rule names a pod that no consumer list names.
- Hosted render: `replicas` is `1` for every workload.
- Local default render: no NetworkPolicy object, and the existing render tests stay green.

Live check (0964 smoke, only on a cluster whose network plugin enforces NetworkPolicy):
- From a pod that no consumer list names, a TCP connection to `gateway-mcp` fails.
- From the `gateway-api` pod, a connection to `game-session` succeeds.

## Definition of Done

- Render tests pass. `helm lint` and `helm template` pass in both modes.
- The live check runs green in the 0964 smoke job on a policy-enforcing network plugin. If the Kind network plugin does not enforce policies, record that in the runbook (0965) and state which job runs the check.
- `docs/reference/hosted-profile.md` lists the exceptions and the policy rules.
- `CHANGELOG.md` `[Unreleased]` entry. Recorded at merge.

## Audit Provenance

- Severity: medium (no security context and no requests; one group does not need autoscaling).
- Source audits: `.audit/research/r1-hosting.md`, sections 8 and 11 (D10, D11). Lines were checked against `main` at `33885a70`.
