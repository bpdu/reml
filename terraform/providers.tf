terraform {
  required_version = ">= 1.7.0"

  required_providers {
    yandex = {
      source  = "yandex-cloud/yandex"
      version = "~> 0.130"
    }
  }

  backend "s3" {
    bucket = "placeholder"
    key    = "placeholder"
    region = "ru-central1"
  }
}

provider "yandex" {
  cloud_id                 = var.yandex_cloud_id
  folder_id                = var.yandex_folder_id
  zone                     = "ru-central1-a"
  service_account_key_file = var.service_account_key_file
}
