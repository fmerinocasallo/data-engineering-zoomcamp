resource "google_compute_instance_template" "co_2vc_8gb" {
  name                 = "co-2vc-8gb"
  instance_description = "GCP Cost Optimized 2 vCPUs & 8 GB RAM"
  machine_type         = "e2-standard-2"

  disk {
    source_image = "debian-cloud/debian-12"
    auto_delete  = true
    boot         = true
    disk_size_gb = 30
  }

  network_interface {
    network = "default"

    # default access config, defining external IP configuration
    access_config {
      network_tier = "STANDARD"
    }
  }

  # # To avoid embedding secret keys or user credentials in the instances, Google recommends that you use custom service accounts with the following access scopes.
  # service_account {
  #   email   = service_account_vm_tf_email
  #   scopes  = [
  #     "https://www.googleapis.com/auth/cloud-platform"
  #   ]
  # }

  # metadata = {
  #   "ssh-keys" = <<EOT
  #     fmerinocasallo:ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBJQRXzWgdYNbY5ZMF+KJQhRGY2ovNJpPcPFX7h7HZao fmerinocasallo
  #    EOT
  # }

}

resource "google_compute_instance_from_template" "tf-instance" {
  name                     = "tf-instance"
  zone                     = var.zone
  source_instance_template = google_compute_instance_template.co_2vc_8gb.self_link_unique
}
