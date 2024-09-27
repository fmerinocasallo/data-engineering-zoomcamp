data "google_service_account_access_token" "vm_tf_impersonation" {
  provider               = google.impersonation
  target_service_account = var.service_account_vm_tf_email
  scopes                 = ["cloud-platform", "userinfo-email"]
  lifetime               = "3600s"
}