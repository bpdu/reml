output "network_id" {
  value = yandex_vpc_network.reml.id
}

output "subnet_a_id" {
  value = yandex_vpc_subnet.reml_a.id
}

output "data_bucket" {
  value = yandex_storage_bucket.reml_data.bucket
}

output "models_bucket" {
  value = yandex_storage_bucket.reml_models.bucket
}