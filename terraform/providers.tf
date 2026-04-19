terraform {
    required_version = ">= 1.7.0"

  required_providers {
    yandex = {
      source  = "yandex-cloud/yandex"
      version = "~> 0.130"
    }
  }
  
  backend "local" {
    path = "terraform.tfstate"
  }
}

provider "yandex" {
  cloud_id  = var.yandex_cloud_id
  folder_id = var.yandex_folder_id
  zone      = "ru-central1-a"
}