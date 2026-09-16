$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$EnvFile = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $EnvFile)) {
    throw "Missing .env file: $EnvFile"
}

Get-Content $EnvFile | ForEach-Object {
    if ($_ -match '^\s*([^#=\s]+)\s*=\s*(.*?)\s*$') {
        $name = $Matches[1]
        $value = $Matches[2].Trim('"', "'")
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

$ProjectId = $env:GOOGLE_CLOUD_PROJECT
$Location = if ($env:BQ_LOCATION) { $env:BQ_LOCATION } else { "US" }
$Dataset = if ($env:POLICY_BQ_DATASET) { $env:POLICY_BQ_DATASET } else { "payer_policy_demo" }
$AdcFile = $env:GOOGLE_APPLICATION_CREDENTIALS

if (-not $ProjectId) { throw "GOOGLE_CLOUD_PROJECT is missing from .env" }
if (-not $AdcFile) { throw "GOOGLE_APPLICATION_CREDENTIALS is missing from .env" }
if (-not (Test-Path $AdcFile)) { throw "ADC credential file not found: $AdcFile" }

$CloudSdkConfig = Join-Path ([IO.Path]::GetTempPath()) ("healthcare-triage-gcloud-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $CloudSdkConfig | Out-Null
$env:CLOUDSDK_CONFIG = $CloudSdkConfig
$env:GOOGLE_APPLICATION_CREDENTIALS = $AdcFile

try {
    gcloud auth activate-service-account `
        --key-file="$AdcFile" `
        --project="$ProjectId" `
        --quiet

    Write-Host "Project:  $ProjectId"
    Write-Host "Location: $Location"
    Write-Host "Dataset:  $Dataset"

    bq --project_id="$ProjectId" mk `
        --dataset `
        --location="$Location" `
        --description="Synthetic payer policy + eligibility data for the healthcare triage ADK demo" `
        "$ProjectId`:$Dataset"

    bq --project_id="$ProjectId" mk `
        --table `
        --clustering_fields=cpt_code,payer_id `
        "$ProjectId`:$Dataset.cpt_rules" `
        "mock_data/bigquery/cpt_rules_schema.json"

    bq --project_id="$ProjectId" load `
        --source_format=NEWLINE_DELIMITED_JSON `
        "$ProjectId`:$Dataset.cpt_rules" `
        "mock_data/bigquery/cpt_rules.jsonl" `
        "mock_data/bigquery/cpt_rules_schema.json"

    bq --project_id="$ProjectId" mk `
        --table `
        --clustering_fields=payer_id,member_id `
        "$ProjectId`:$Dataset.member_eligibility" `
        "mock_data/bigquery/member_eligibility_schema.json"

    bq --project_id="$ProjectId" load `
        --source_format=NEWLINE_DELIMITED_JSON `
        "$ProjectId`:$Dataset.member_eligibility" `
        "mock_data/bigquery/member_eligibility.jsonl" `
        "mock_data/bigquery/member_eligibility_schema.json"

    bq --project_id="$ProjectId" query --nouse_legacy_sql --format=pretty `
        "SELECT COUNT(*) AS cpt_rules_rows FROM ``$ProjectId.$Dataset.cpt_rules``"
    bq --project_id="$ProjectId" query --nouse_legacy_sql --format=pretty `
        "SELECT COUNT(*) AS eligibility_rows FROM ``$ProjectId.$Dataset.member_eligibility``"

    $ProjectNumber = gcloud projects describe $ProjectId --format="value(projectNumber)"
    $RuntimeServiceAgent = "service-$ProjectNumber@gcp-sa-aiplatform-re.iam.gserviceaccount.com"

    bq --project_id="$ProjectId" update --dataset `
        --add_iam_member="serviceAccount:$RuntimeServiceAgent:roles/bigquery.dataViewer" `
        "$ProjectId`:$Dataset"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not grant BigQuery dataViewer to $RuntimeServiceAgent. Run the IAM grant with an administrator account."
    }

    gcloud projects add-iam-policy-binding $ProjectId `
        --member="serviceAccount:$RuntimeServiceAgent" `
        --role="roles/bigquery.jobUser" `
        --condition=None
    if ($LASTEXITCODE -ne 0) {
        throw "Could not grant BigQuery jobUser to $RuntimeServiceAgent. Run the IAM grant with an administrator account."
    }

    Write-Host "BigQuery setup completed successfully."
}
finally {
    Remove-Item -Recurse -Force $CloudSdkConfig -ErrorAction SilentlyContinue
    Remove-Item Env:CLOUDSDK_CONFIG -ErrorAction SilentlyContinue
}
