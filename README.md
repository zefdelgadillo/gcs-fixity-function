# Fixity Metadata for GCS
This script pulls metadata and checksums for file archives in GCS and stores them in a manifest file and in BigQuery to track changes over time. The script uses the [BagIt](https://tools.ietf.org/html/draft-kunze-bagit-17) specification.

## Overview
Files should be stored in a GCS bucket in _bag_, or a directory in GCS bucket. In that bag, the script will generate a manifest file and keep track of changes over time in a BigQuery dataset.

The script here is a Cloud Function that listens on changes to a GCS bucket, then pulls metadata to create a manifest file with the md5sum, and save that information in BigQuery for reporting and audit purposes.

Here is an example file structure for a bag titled `my-bag`. Archived files should be uploaded into a `data/` directory.
```
.
├── my-bag
│   ├── manifest-md5sum.txt
│   └── data
│       ├── file1.zip
│       └── file2.zip
```

## Setup
First, set your project by using `gcloud config set project <my-project>`
Set the following environment variables:
```
export PROJECT_ID=<my-project-id>
export BUCKET_NAME=<my-target-bucket-name>
export BAG_NAME=<my-target-bag-name>
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
3. Upload files using the structure `gs://$BUCKET_NAME/$BAG_NAME/data/<file>`. Note: It's a good idea to bulk upload files _before_ deploying/invoking the Fixity script, since each file upload will trigger a script invokation for each uploaded file if the script is deployed first.
```
gsutil cp * gs://$BUCKET_NAME/$BAG_NAME/data/
```
If you know the MD5 of a file before uploading you can specify it in the Content-MD5 header, which will cause the cloud storage service to reject the upload if the MD5 doesn't match the value computed by the service. See more [here](https://cloud.google.com/storage/docs/gsutil/commands/cp#checksum-validation)

### BigQuery Setup
This should be run *once*.

Run the `./scripts/setup-dataset.sh` script creates the following resources:
* `fixityData` and `fixity` datasets.
* `fixityData.records` table to hold each individual Fixity record for every invokation.
* `fixity.current_manifest` view to show the current manifest of files for a bag.
* `fixity.file_operations` view to show all operations and diffs across time for a bag.

### Cloud Function Setup
The following commands should be run *once for each bag* ensuring PROJECT_ID, BUCKET_NAME, and BAG_NAME are already set.

These commands will deploy the Cloud Function that tracks your bucket.
```
gcloud functions deploy track-deletes-$BUCKET_NAME-$BAG_NAME --source=./src/ --entry-point main --runtime python37 --trigger-resource $BUCKET_NAME --trigger-event google.storage.object.archive --set-env-vars BUCKET=$BUCKET_NAME,BAG=$BAG_NAME
gcloud functions deploy track-updates-$BUCKET_NAME-$BAG_NAME --source=./src/ --entry-point main --runtime python37 --trigger-resource $BUCKET_NAME --trigger-event google.storage.object.finalize --set-env-vars BUCKET=$BUCKET_NAME,BAG=$BAG_NAME
gcloud functions deploy manual-$BUCKET_NAME-$BAG_NAME --source=./src/ --entry-point main --runtime python37 --trigger-http --set-env-vars BUCKET=$BUCKET_NAME,BAG=$BAG_NAME
```

## License
Copyright 2019 Google LLC. This software is provided as-is, without warranty or representation for any use or purpose. Your use of it is subject to your agreement with Google.  