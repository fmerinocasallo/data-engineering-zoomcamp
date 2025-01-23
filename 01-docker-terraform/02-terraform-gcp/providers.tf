terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "6.2.0"
    }
  }
}

# Impersonation provider to manage VM instances with Terraform
provider "google" {
  alias = "impersonation"
  scopes = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
  ]
}

# Default provider that will impersonate the provider managing VM instances with Terraform
provider "google" {
  project         = var.project_id
  region          = var.region
  zone            = var.zone
  access_token    = data.google_service_account_access_token.vm_tf_impersonation.access_token
  request_timeout = "60s"
  # credentials = file(var.credentials)
}