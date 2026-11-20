{{/*
True (non-empty) when the render is a hosted profile: global.environment is staging or production.
Call with $ and test the result with `if include`. The local render returns an empty string.
Hosted-only objects and settings (TASK-0962) use this switch.
*/}}
{{- define "runefoble.hosted.profile" -}}
{{- if or (eq .Values.global.environment "staging") (eq .Values.global.environment "production") -}}true{{- end -}}
{{- end -}}
