output "cluster_name"      { value = google_dataproc_cluster.main.name }
output "cluster_master_ip" { value = google_dataproc_cluster.main.cluster_config[0].master_config[0].instance_names[0] }
