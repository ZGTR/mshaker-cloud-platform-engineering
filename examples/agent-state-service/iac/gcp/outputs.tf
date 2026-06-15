output "cluster_name" {
  value = google_container_cluster.this.name
}

output "region" {
  value = var.region
}

output "configure_kubectl" {
  description = "Run this to update your kubeconfig"
  value       = "gcloud container clusters get-credentials ${google_container_cluster.this.name} --region ${var.region} --project ${var.project_id}"
}
