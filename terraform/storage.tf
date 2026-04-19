resource "yandex_storage_bucket" "reml_data" {
  bucket   = "reml-data"
  max_size = 100 * 1024 * 1024 * 1024
}

resource "yandex_storage_bucket" "reml_models" {
  bucket   = "reml-models"
  max_size = 50 * 1024 * 1024 * 1024
}
