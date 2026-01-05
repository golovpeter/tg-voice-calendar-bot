{{/*
Expand the name of the chart.
*/}}
{{- define "tg-calendar-bot.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "tg-calendar-bot.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "tg-calendar-bot.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "tg-calendar-bot.labels" -}}
helm.sh/chart: {{ include "tg-calendar-bot.chart" . }}
{{ include "tg-calendar-bot.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "tg-calendar-bot.selectorLabels" -}}
app.kubernetes.io/name: {{ include "tg-calendar-bot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Bot labels
*/}}
{{- define "tg-calendar-bot.bot.labels" -}}
{{ include "tg-calendar-bot.labels" . }}
app.kubernetes.io/component: bot
{{- end }}

{{/*
Bot selector labels
*/}}
{{- define "tg-calendar-bot.bot.selectorLabels" -}}
{{ include "tg-calendar-bot.selectorLabels" . }}
app.kubernetes.io/component: bot
{{- end }}

{{/*
Redis labels
*/}}
{{- define "tg-calendar-bot.redis.labels" -}}
app.kubernetes.io/name: {{ .Values.redis.name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: redis
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Redis selector labels
*/}}
{{- define "tg-calendar-bot.redis.selectorLabels" -}}
app.kubernetes.io/name: {{ .Values.redis.name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: redis
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "tg-calendar-bot.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "tg-calendar-bot.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Redis URL
*/}}
{{- define "tg-calendar-bot.redisUrl" -}}
{{- if .Values.bot.env.redisUrl }}
{{- .Values.bot.env.redisUrl }}
{{- else }}
{{- printf "redis://%s:6379/0" .Values.redis.name }}
{{- end }}
{{- end }}

{{/*
Namespace
*/}}
{{- define "tg-calendar-bot.namespace" -}}
{{- if .Values.namespace.create }}
{{- .Values.namespace.name }}
{{- else }}
{{- .Release.Namespace }}
{{- end }}
{{- end }}

