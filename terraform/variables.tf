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

variable "ssh_public_key_path" {
  description = "Path to SSH public key file"
  type        = string
}

variable "ssh_private_key_path" {
  description = "Path to SSH private key file"
  type        = string
}

variable "ssh_username" {
  description = "SSH username for the instance"
  type        = string
  default     = "ubuntu"
}

variable "environment" {
  description = "Deployment environment name"
  type        = string

  validation {
    condition     = contains(["test", "prod"], var.environment)
    error_message = "environment must be one of: test, prod."
  }
}

variable "postgres_user" {
  description = "PostgreSQL application username"
  type        = string
  sensitive   = true
}

variable "postgres_password" {
  description = "PostgreSQL application password"
  type        = string
  sensitive   = true
}

variable "clickhouse_user" {
  description = "ClickHouse application username"
  type        = string
  sensitive   = true
}

variable "clickhouse_password" {
  description = "ClickHouse application password"
  type        = string
  sensitive   = true
}

variable "basic_auth_username" {
  description = "Username for nginx basic auth"
  type        = string
  sensitive   = true
}

variable "basic_auth_password" {
  description = "Password for nginx basic auth"
  type        = string
  sensitive   = true
}

variable "ssh_allowed_ips" {
  description = "Public IP addresses allowed to access SSH"
  type        = list(string)
}

variable "observability_allowed_ip" {
  description = "Public IP address allowed to scrape Node Exporter"
  type        = string
}

variable "ui_allowed_ips" {
  description = "Public IP addresses allowed to access Prefect and MLflow via nginx"
  type        = list(string)
}

variable "node_exporter_port" {
  description = "Prometheus Node Exporter port"
  type        = number
  default     = 9100
}

variable "loki_push_url" {
  description = "Loki push API URL for Promtail"
  type        = string
}
