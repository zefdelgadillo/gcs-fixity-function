# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
prepare:
		./setup-bigquery.sh

.PHONY: deploy
deploy:
		gcloud functions deploy track-deletes-${BUCKET_NAME} --source=./src/ --entry-point main --runtime python37 --trigger-resource ${BUCKET_NAME} --trigger-event google.storage.object.archive --set-env-vars BUCKET=${BUCKET_NAME}
		gcloud functions deploy track-updates-${BUCKET_NAME} --source=./src/ --entry-point main --runtime python37 --trigger-resource ${BUCKET_NAME} --trigger-event google.storage.object.finalize --set-env-vars BUCKET=${BUCKET_NAME}
		gcloud functions deploy manual-${BUCKET_NAME} --source=./src/ --entry-point main --runtime python37 --trigger-http --set-env-vars BUCKET=${BUCKET_NAME}
