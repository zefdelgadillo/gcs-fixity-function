#!/usr/bin/env bash
PROJECT_ID=$(gcloud config get-value project)
bq show fixityData > /dev/null

# Create datasets
if [ $? -eq 0 ]
then
  echo "fixityData dataset already created" >&2
else
  bq --location=US mk -d \
  --description "Fixity metadata" \
  fixityData
fi
bq show fixity > /dev/null
if [ $? -eq 0 ]
then
  echo "fixity dataset already created" >&2
else
  bq --location=US mk -d \
  --description "Fixity metadata views" \
  fixity
fi

# Create table for records
bq show fixityData.records > /dev/null
if [ $? -eq 0 ]
then
  echo "fixity table already created" >&2
else
  bq mk --table \
  --description "Table for fixity records" \
  fixityData.records \
  ./scripts/schema.json
fi

# Create views
bq show fixity.current_manifest > /dev/null
if [ $? -eq 0 ]
then
  echo "current manifest view already created" >&2
else
  MANIFEST_VIEW=$(sed "s/PROJECT_ID/$PROJECT_ID/g" ./scripts/current-manifest.sql)
  bq mk \
  --use_legacy_sql=false \
  --description "View showing current manifest of files" \
  --view "$MANIFEST_VIEW" \
  fixity.current_manifest
fi
bq show fixity.file_operations > /dev/null
if [ $? -eq 0 ]
then
  echo "file operations view already created" >&2
else
  OPERATIONS_VIEW=$(sed "s/PROJECT_ID/$PROJECT_ID/g" ./scripts/file-operations.sql)
  bq mk \
  --use_legacy_sql=false \
  --description "View showing list of all file operations" \
  --view "$OPERATIONS_VIEW" \
  fixity.file_operations
fi