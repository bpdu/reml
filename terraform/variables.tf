variable "yandex_cloud_id" {
  description = "Yandex Cloud ID"
  type        = string
  sensitive   = true
}

variable "yandex_folder_id" {
  description = "Yandex Folder ID"
  type        = string
  sensitive   = true
}

variable "service_account_key_file" {
  description = "Path to service account JSON key file"
  type        = string
  sensitive   = true
}
