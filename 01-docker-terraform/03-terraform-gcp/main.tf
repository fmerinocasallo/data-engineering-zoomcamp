# resource "google_storage_bucket" "demo-bucket" {
#   name          = var.gcs_bucket_name
#   location      = var.location
#   force_destroy = true

#   lifecycle_rule {
#     condition {
#       age = 1
#     }
#     action {
#       type = "AbortIncompleteMultipartUpload"
#     }
#   }
# }

# resource "google_bigquery_dataset" "demo-dataset" {
#   dataset_id = var.bq_dataset_id
#   location   = var.location
# }