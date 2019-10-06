# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.cloud import storage, bigquery
import base64
import binascii
import os
import re
from flask import escape
from datetime import datetime

fixity_date = datetime.now()

def main(bucket={}, event={}):
    if event != {}:
        fail_on_manifest(event)
    bucket_name = os.environ['BUCKET']
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    bags = get_bags(bucket, None)
    matched_bags = match_bag(event, bags)
    for bag in matched_bags:
        bagit = BagIt(bucket, bag)
        bagit.write_and_upload_manifest()
        bagit.write_to_bigquery()

def match_bag(event, bags):
    if event == {}:
        return bags
    filename = event.resource['name']
    for bag in bags:
        if bag in filename:
            return [bag]

def get_bags(bucket, top_prefix=None):
    # Recurse through directory tree until you hit 'data/' to create a list of every bag
    prefixes = []
    top_prefixes = get_prefixes(bucket, top_prefix)
    for prefix in top_prefixes:
        if prefix.endswith('data/'):
            prefixes.append(re.sub('\/data\/$', '', prefix)) # remove data/ from bag name
        else:
            prefixes += get_bags(bucket, prefix)
    return prefixes

def get_prefixes(bucket, prefix=None):
    iterator = bucket.list_blobs(prefix=prefix, delimiter="/")
    response = iterator._get_next_page_response()
    return response['prefixes']

def fail_on_manifest(event):
    filename = event.resource['name']
    if 'manifest-md5sum.txt' in filename:
        exit(0)

class BagIt:
    def __init__ (self, bucket, bag):
        self.bag = bag
        self.bucket_name = os.environ['BUCKET']
        self.bucket = bucket
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
        dataset_id = 'fixity_data'  # replace with your dataset ID
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
