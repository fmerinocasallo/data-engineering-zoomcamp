output "instance_external_ip" {
  description = "External IP address of the VM instance"
  value       = google_compute_instance_from_template.tf-instance.network_interface[0].access_config[0].nat_ip
}