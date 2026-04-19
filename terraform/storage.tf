resource "yandex_storage_bucket" "reml_data" {
  bucket     = "reml-data"
  acl        = "private"
  max_size   = 100 * 1024 * 1024 * 1024
}

resource "yandex_storage_bucket" "reml_models" {
  bucket     = "reml-models"
  acl        = "private"
  max_size   = 50 * 1024 * 1024 * 1024
}
