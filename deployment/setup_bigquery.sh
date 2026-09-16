#!/usr/bin/env bash
# Provisions the BigQuery side of the demo. Run once per project.
# Requires: gcloud + bq CLIs. Both use the JSON credential file configured
# below; the script does not depend on or modify the terminal's active account.

set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT first}"
LOCATION="${BQ_LOCATION:-US}"                 # match your Agent Runtime region's multi-region, e.g. US or EU
DATASET="${POLICY_BQ_DATASET:-payer_policy_demo}"
ADC_FILE="${GOOGLE_APPLICATION_CREDENTIALS:-C:/Users/nikhi/Desktop/Projects/GE Webinar/d3v-agentspace-demo-4c8cfd668d80.json}"

if [[ ! -f "${ADC_FILE}" ]]; then
  echo "ADC credential file not found: ${ADC_FILE}" >&2
  exit 1
fi

# Use an isolated Cloud SDK configuration so bq and gcloud both authenticate
# with this file without changing the user's normal gcloud account.
export GOOGLE_APPLICATION_CREDENTIALS="${ADC_FILE}"
export CLOUDSDK_CONFIG="$(mktemp -d)"
cleanup() {
  rm -rf "${CLOUDSDK_CONFIG}"
}
trap cleanup EXIT
gcloud auth activate-service-account \
  --key-file="${ADC_FILE}" \
  --project="${PROJECT_ID}" \
  --quiet

echo "Project:  ${PROJECT_ID}"
echo "Location: ${LOCATION}"
echo "Dataset:  ${DATASET}"

# 1. Dataset
bq --project_id="${PROJECT_ID}" mk \
  --dataset \
  --location="${LOCATION}" \
  --description "Synthetic payer policy + eligibility data for the healthcare triage ADK demo" \
  "${PROJECT_ID}:${DATASET}" || echo "Dataset already exists, continuing."

# 2. cpt_rules table -- clustered on cpt_code and payer_id since those are
#    the lookup keys the coverage_evaluator tool filters on.
bq --project_id="${PROJECT_ID}" mk \
  --table \
  --clustering_fields=cpt_code,payer_id \
  "${PROJECT_ID}:${DATASET}.cpt_rules" \
  mock_data/bigquery/cpt_rules_schema.json

bq --project_id="${PROJECT_ID}" load \
  --source_format=NEWLINE_DELIMITED_JSON \
  "${PROJECT_ID}:${DATASET}.cpt_rules" \
  mock_data/bigquery/cpt_rules.jsonl \
  mock_data/bigquery/cpt_rules_schema.json

# 3. member_eligibility table -- clustered on payer_id, member_id (composite
#    lookup key used by check_member_eligibility).
bq --project_id="${PROJECT_ID}" mk \
  --table \
  --clustering_fields=payer_id,member_id \
  "${PROJECT_ID}:${DATASET}.member_eligibility" \
  mock_data/bigquery/member_eligibility_schema.json

bq --project_id="${PROJECT_ID}" load \
  --source_format=NEWLINE_DELIMITED_JSON \
  "${PROJECT_ID}:${DATASET}.member_eligibility" \
  mock_data/bigquery/member_eligibility.jsonl \
  mock_data/bigquery/member_eligibility_schema.json

echo ""
echo "Tables loaded. Row counts:"
bq --project_id="${PROJECT_ID}" query --nouse_legacy_sql --format=pretty \
  "SELECT COUNT(*) AS cpt_rules_rows FROM \`${PROJECT_ID}.${DATASET}.cpt_rules\`"
bq --project_id="${PROJECT_ID}" query --nouse_legacy_sql --format=pretty \
  "SELECT COUNT(*) AS eligibility_rows FROM \`${PROJECT_ID}.${DATASET}.member_eligibility\`"

# 4. IAM: grant the Agent Runtime (Reasoning Engine) service agent read +
#    query-job access. This is the identity your deployed agent actually
#    runs as -- NOT a downloaded key. Get PROJECT_NUMBER first:
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
RE_SERVICE_AGENT="service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"

echo ""
echo "Granting BigQuery access to Agent Runtime service agent: ${RE_SERVICE_AGENT}"

bq --project_id="${PROJECT_ID}" add-iam-policy-binding \
  --member="serviceAccount:${RE_SERVICE_AGENT}" \
  --role="roles/bigquery.dataViewer" \
  "${DATASET}"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${RE_SERVICE_AGENT}" \
  --role="roles/bigquery.jobUser" \
  --condition=None

echo "Done. Update your .env with POLICY_BQ_DATASET=${DATASET} and BQ_LOCATION=${LOCATION}."
