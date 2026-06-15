provider "google" {
  project = var.project_id
  region  = var.region
}

# Regional cluster. metrics-server + HPA are built into GKE, so no extra
# install is needed (unlike EKS).
resource "google_container_cluster" "this" {
  name     = var.cluster_name
  location = var.region

  # Best practice: create the cluster with the default node pool, then remove
  # it and manage our own pool below.
  remove_default_node_pool = true
  initial_node_count       = 1

  deletion_protection = false

  release_channel {
    channel = "REGULAR"
  }
}

resource "google_container_node_pool" "default" {
  name     = "default"
  cluster  = google_container_cluster.this.id
  location = var.region

  node_count = var.node_count

  autoscaling {
    min_node_count = var.min_node_count
    max_node_count = var.max_node_count
  }

  node_config {
    machine_type = var.machine_type
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}
