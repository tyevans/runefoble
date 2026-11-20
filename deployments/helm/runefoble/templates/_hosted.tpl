{{/*
True (non-empty) when the render is a hosted profile: global.environment is staging or production.
Call with $ and test the result with `if include`. The local render returns an empty string.
Hosted-only objects and settings (TASK-0962) use this switch.
*/}}
{{- define "runefoble.hosted.profile" -}}
{{- if or (eq .Values.global.environment "staging") (eq .Values.global.environment "production") -}}true{{- end -}}
{{- end -}}

{{/*
Pod security context of a hosted workload (TASK-0962). Seccomp RuntimeDefault for every pod. Call
with (dict "extra" <the service's podSecurityContext, or nil>) and pipe to nindent. The extra keys
(for example fsGroup) stay, and the seccomp profile is added to them.
*/}}
{{- define "runefoble.hosted.podSecurity" -}}
{{- $sc := deepCopy (.extra | default dict) -}}
{{- $_ := set $sc "seccompProfile" (dict "type" "RuntimeDefault") -}}
{{- toYaml $sc -}}
{{- end -}}

{{/*
Container security context of an application container that runs as a non-root UID from its
Dockerfile (ADR-0015). It drops every capability and blocks privilege escalation. Call with
(dict "uid" <numeric UID> "readOnly" <true or false>) and pipe to nindent. Set readOnly to true
only after the service is checked for writes outside /tmp (the chart mounts /tmp as an emptyDir).
*/}}
{{- define "runefoble.hosted.appContainerSecurity" -}}
allowPrivilegeEscalation: false
capabilities:
  drop:
    - ALL
runAsNonRoot: true
runAsUser: {{ .uid }}
readOnlyRootFilesystem: {{ .readOnly }}
{{- end -}}

{{/*
Container security context of a third-party container. The image chooses its own user and some
images need root at start-up, so only privilege escalation is blocked here. The exceptions are
listed in docs/reference/hosted-profile.md, section "Security exceptions".
*/}}
{{- define "runefoble.hosted.thirdPartyContainerSecurity" -}}
allowPrivilegeEscalation: false
{{- end -}}
