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

Run `make prepare` script creates the following resources:

* `fixity_data` and `fixity` datasets.
* `fixity_data.records` table to hold each individual Fixity record for every invokation.
* `fixity.current_manifest` view to show the current manifest of files for a bag.
* `fixity.file_operations` view to show all operations and diffs across time for a bag.

### Cloud Function Setup
The following commands should be run *once for each bucket* ensuring PROJECT_ID, and BUCKET_NAME are already set.

Ensure `BUCKET_NAME` is set to your bucket name using `export BUCKET_NAME=<bucket-name>`.
Run `make deploy`, which will deploy the Cloud Functions required for the operation:

* `track-deletes`: Runs Fixity check any time a file is archived.
* `track-updates`: Runs Fixity check any time a file is created or changed.
* `manual`: Enables Fixity runs that can be scheduled or invoked manually.

### Scheduler Setup
To create a schedule, use the following command. The default recommended below will run on the 1st of every month at 8:00 am.

Once the following has been created, you can run Fixity on demand by visiting https://console.cloud.google.com/cloudscheduler.
```
export SCHEDULE="1 of month 08:00"
gcloud scheduler jobs create pubsub fixity-${BUCKET_NAME} --schedule="${SCHEDULE}" --topic=fixity-${BUCKET_NAME}-topic --message-body={} 
```
