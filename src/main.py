from google.cloud import storage, bigquery
import base64
import binascii
import os
from flask import escape
from datetime import datetime

def main(bucket={}, event={}):
    if event != {}:
        fail_on_manifest(event)
    bagit = BagIt(os.environ['BUCKET'], os.environ['BAG'])
    bagit.write_and_upload_manifest()
    bagit.write_to_bigquery()

def fail_on_manifest(event):
    filename = event.resource['name']
    if 'manifest-md5sum.txt' in filename:
        exit(0)

class BagIt:
    def __init__ (self, bucket, bag):
        storage_client = storage.Client()
        self.bucket_name = bucket
        self.bag = bag
        self.bucket = storage_client.get_bucket(bucket)
        self.blobs = self.get_blobs()
        self.bigquery_client = bigquery.Client()

    def get_blobs(self):
        blobs = self.bucket.list_blobs(prefix=f'{self.bag}/data/')
        blobs_with_metadata = []
        for blob in blobs:
            blobs_with_metadata.append(self.get_metadata(blob.name))
        return blobs_with_metadata

    def decode_hash(self, bytes):
        return binascii.hexlify(base64.urlsafe_b64decode(bytes)).decode('utf-8')

    def get_metadata(self, blob_name):
        blob = self.bucket.get_blob(blob_name)
        return {
            'name': blob.name,
            'id': blob.id,
            'size': blob.size,
            'updated': blob.updated,
            'crc32c': self.decode_hash(blob.crc32c),
            'md5sum': self.decode_hash(blob.md5_hash)
        }

    def write_to_bigquery(self):
        fixity_date = datetime.now()
        dataset_id = 'fixityData'  # replace with your dataset ID
        table_id = 'records'  # replace with your table ID
        table_ref = self.bigquery_client.dataset(dataset_id).table(table_id)
        table = self.bigquery_client.get_table(table_ref)  # API request
        rows_to_insert = list(map(lambda blob: (self.bucket_name, self.bag, blob['name'], blob['size'], blob['updated'], blob['crc32c'], blob['md5sum'], fixity_date), self.blobs))
        self.bigquery_client.insert_rows(table, rows_to_insert)

    def write_and_upload_manifest(self):
        manifest = ""
        for blob in self.blobs:
            manifest = manifest + blob['name'] + '\t' + blob['md5sum'] + '\n'
        
        manifest_blob = self.bucket.blob(f'{self.bag}/manifest-md5sum.txt')
        manifest_blob.upload_from_string(manifest)
