# variable "credentials" {
#   type        = string
#   description = "GCP Credentials (Service Account Key)"
# }

variable "project_id" {
  type        = string
  description = "ID of the project in scope"
}

variable "region" {
  type        = string
  description = "Default project region"
}

variable "zone" {
  type        = string
  description = "Default project zone"

}

variable "location" {
  type        = string
  description = "Project Location"
}

variable "service_account_vm_tf_email" {
  type        = string
  description = "Email adress of the service account used to manage VM instances with Terraform"
}
