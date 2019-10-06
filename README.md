# Fixity Metadata for GCS 🗃
This script pulls metadata and checksums for file archives in Google Cloud Storage and stores them in a manifest file and in BigQuery to track changes over time. The script uses the [BagIt](https://tools.ietf.org/html/draft-kunze-bagit-17) specification.

## Overview
Files should be stored in a GCS bucket in _bag_, or a directory in GCS bucket. In that bag, the script will generate a manifest file and keep track of changes over time in a BigQuery dataset.

The script here is a Cloud Function that listens on changes to a GCS bucket, then pulls metadata to create a manifest file with the md5sum, and save that information in BigQuery for reporting and audit purposes.

The script supports as many bags as you'd like to define for a single Bucket. A Bag is defined as a directory containing a `data/` directory. The example below constitutes 3 different bags: `col1/bag1`, `col1/bag2`, and `col1/bag1`. Bags can be nested in collections or folders as long as they contain a `data/` directory.
```
.
├── col1
│   ├── bag1
│   │   └── data
│   │       ├── a
│   │       ├── b
│   │       └── c
│   └── bag2
│       └── data
│           ├── a
│           ├── b
│           └── c
├── col2
│   ├── bag1
│   │   └── data
│   │       ├── a
│   │       ├── b
│   │       └── c
```

## Setup
First, set your project by using `gcloud config set project <my-project>`
Set the following environment variables:
```
export PROJECT_ID=<my-project-id>
export BUCKET_NAME=<my-target-bucket-name>
```

### GCS Bucket Setup
1. [Create a GCS bucket](https://cloud.google.com/storage/docs/creating-buckets#storage-create-bucket-gsutil) that will contain your file archive bag(s).
```
gsutil mb gs://$BUCKET_NAME
```
2. Turn on [file versioning](https://cloud.google.com/storage/docs/object-versioning) for your GCS bucket to ensure files are never overwritten.
```
gsutil versioning set on gs://$BUCKET_NAME
```
3. Upload files using the structure into the `data/` directories created for each Bag. Note: It's a good idea to bulk upload files _before_ deploying/invoking the Fixity script, since each file upload will trigger a script invokation for each uploaded file if the script is deployed first.
```
gsutil cp * gs://$BUCKET_NAME/<bag_path>/data/
```
If you know the MD5 of a file before uploading you can specify it in the Content-MD5 header, which will cause the cloud storage service to reject the upload if the MD5 doesn't match the value computed by the service. See more [here](https://cloud.google.com/storage/docs/gsutil/commands/cp#checksum-validation)

### BigQuery Setup
This should be run *once*.

Run the `./setup-bigquery.sh` script creates the following resources:
* `fixityData` and `fixity` datasets.
* `fixityData.records` table to hold each individual Fixity record for every invokation.
* `fixity.current_manifest` view to show the current manifest of files for a bag.
* `fixity.file_operations` view to show all operations and diffs across time for a bag.

### Cloud Function Setup
The following commands should be run *once for each bucket* ensuring PROJECT_ID, and BUCKET_NAME are already set.

These commands will deploy the Cloud Function that tracks your bucket.
```
gcloud functions deploy track-deletes-$BUCKET_NAME --source=./src/ --entry-point main --runtime python37 --trigger-resource $BUCKET_NAME --trigger-event google.storage.object.archive --set-env-vars BUCKET=$BUCKET_NAME
gcloud functions deploy track-updates-$BUCKET_NAME --source=./src/ --entry-point main --runtime python37 --trigger-resource $BUCKET_NAME --trigger-event google.storage.object.finalize --set-env-vars BUCKET=$BUCKET_NAME
gcloud functions deploy manual-$BUCKET_NAME --source=./src/ --entry-point main --runtime python37 --trigger-http --set-env-vars BUCKET=$BUCKET_NAME
```
