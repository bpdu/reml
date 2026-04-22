data "yandex_compute_image" "ubuntu" {
  family = "ubuntu-2404-lts"
}

locals {
  postgres_db   = "reml_${var.environment}"
  clickhouse_db = "reml_${var.environment}"
}

check "workspace_matches_environment" {
  assert {
    condition     = terraform.workspace == var.environment
    error_message = "terraform workspace must match var.environment."
  }
}

resource "yandex_compute_instance" "reml_controller" {
  name        = "reml-controller"
  platform_id = "standard-v3"
  zone        = "ru-central1-a"

  resources {
    cores  = 2
    memory = 8
  }

  boot_disk {
    initialize_params {
      image_id = data.yandex_compute_image.ubuntu.image_id
      size     = 50
      type     = "network-ssd"
    }
  }

  network_interface {
    subnet_id          = yandex_vpc_subnet.reml_a.id
    nat                = true
    nat_ip_address     = yandex_vpc_address.reml_static.external_ipv4_address[0].address
    security_group_ids = [yandex_vpc_security_group.reml_controller.id]
  }

  metadata = {
    ssh-keys = "${var.ssh_username}:${chomp(file(var.ssh_public_key_path))}"
    user-data = templatefile("${path.module}/templates/cloud-init.tpl", {
      ssh_username   = var.ssh_username
      ssh_public_key = chomp(file(var.ssh_public_key_path))
    })
  }

  # Provisioner 1: Prefect nginx config
  provisioner "file" {
    content = templatefile("${path.module}/templates/prefect.nginx.tpl", {
      ui_allowed_ips = var.ui_allowed_ips
    })
    destination = "/tmp/prefect.nginx.conf"

    connection {
      type        = "ssh"
      user        = var.ssh_username
      private_key = file(var.ssh_private_key_path)
      host        = self.network_interface[0].nat_ip_address
    }
  }

  # Provisioner 2: MLflow nginx config
  provisioner "file" {
    content = templatefile("${path.module}/templates/mlflow.nginx.tpl", {
      ui_allowed_ips = var.ui_allowed_ips
    })
    destination = "/tmp/mlflow.nginx.conf"

    connection {
      type        = "ssh"
      user        = var.ssh_username
      private_key = file(var.ssh_private_key_path)
      host        = self.network_interface[0].nat_ip_address
    }
  }

  # Provisioner 3: Prefect systemd service
  provisioner "file" {
    source      = "${path.module}/templates/prefect.service.tpl"
    destination = "/tmp/prefect.service"

    connection {
      type        = "ssh"
      user        = var.ssh_username
      private_key = file(var.ssh_private_key_path)
      host        = self.network_interface[0].nat_ip_address
    }
  }

  # Provisioner 4: MLflow systemd service
  provisioner "file" {
    source      = "${path.module}/templates/mlflow.service.tpl"
    destination = "/tmp/mlflow.service"

    connection {
      type        = "ssh"
      user        = var.ssh_username
      private_key = file(var.ssh_private_key_path)
      host        = self.network_interface[0].nat_ip_address
    }
  }

  # Provisioner 5: ClickHouse compose file
  provisioner "file" {
    content = templatefile("${path.module}/templates/clickhouse.compose.tpl", {
      clickhouse_db       = local.clickhouse_db
      clickhouse_user     = var.clickhouse_user
      clickhouse_password = var.clickhouse_password
    })
    destination = "/tmp/clickhouse.compose.yml"

    connection {
      type        = "ssh"
      user        = var.ssh_username
      private_key = file(var.ssh_private_key_path)
      host        = self.network_interface[0].nat_ip_address
    }
  }

  # Provisioner 6: PostgreSQL bootstrap
  provisioner "remote-exec" {
    inline = [
      "set -e",
      "sudo cloud-init status --wait",
      "sudo systemctl enable postgresql",
      "sudo systemctl start postgresql",
      "sudo bash -lc 'PG_VERSION=$(ls /etc/postgresql | sort -V | tail -n1); CONF=/etc/postgresql/$${PG_VERSION}/main/postgresql.conf; if grep -Eq \"^[#[:space:]]*listen_addresses[[:space:]]*=\" \"$CONF\"; then sed -Ei \"s|^[#[:space:]]*listen_addresses[[:space:]]*=.*|listen_addresses = \\\"127.0.0.1\\\"|\" \"$CONF\"; else echo \"listen_addresses = \\\"127.0.0.1\\\"\" >> \"$CONF\"; fi'",
      "sudo bash -lc 'PG_VERSION=$(ls /etc/postgresql | sort -V | tail -n1); HBA=/etc/postgresql/$${PG_VERSION}/main/pg_hba.conf; grep -Eq \"^host[[:space:]]+all[[:space:]]+all[[:space:]]+127\\\\.0\\\\.0\\\\.1/32[[:space:]]+scram-sha-256$\" \"$HBA\" || printf \"%s\\n\" \"host all all 127.0.0.1/32 scram-sha-256\" >> \"$HBA\"'",
      "sudo systemctl restart postgresql",
      "sudo -u postgres psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname = '${replace(var.postgres_user, "'", "''")}'\" | grep -q 1 || sudo -u postgres psql -c \"CREATE ROLE \\\"${var.postgres_user}\\\" LOGIN\"",
      "sudo -u postgres psql -c \"ALTER ROLE \\\"${var.postgres_user}\\\" WITH PASSWORD '${replace(var.postgres_password, "'", "''")}'\"",
      "sudo -u postgres psql -tAc \"SELECT 1 FROM pg_database WHERE datname = '${local.postgres_db}'\" | grep -q 1 || sudo -u postgres psql -c \"CREATE DATABASE \\\"${local.postgres_db}\\\" OWNER \\\"${var.postgres_user}\\\"\"",
      "sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE \\\"${local.postgres_db}\\\" TO \\\"${var.postgres_user}\\\"\""
    ]

    connection {
      type        = "ssh"
      user        = var.ssh_username
      private_key = file(var.ssh_private_key_path)
      host        = self.network_interface[0].nat_ip_address
    }
  }

  # Provisioner 7: ClickHouse bootstrap
  provisioner "remote-exec" {
    inline = [
      "set -e",
      "sudo cloud-init status --wait",
      "mkdir -p /home/${var.ssh_username}/clickhouse",
      "cp /tmp/clickhouse.compose.yml /home/${var.ssh_username}/clickhouse/docker-compose.yml",
      "docker compose -f /home/${var.ssh_username}/clickhouse/docker-compose.yml up -d",
      "for i in $(seq 1 30); do docker exec clickhouse-server clickhouse-client --user '${var.clickhouse_user}' --password '${var.clickhouse_password}' --query 'SELECT 1' && exit 0; sleep 2; done; exit 1",
      "docker exec clickhouse-server clickhouse-client --user '${var.clickhouse_user}' --password '${var.clickhouse_password}' --query 'CREATE DATABASE IF NOT EXISTS ${local.clickhouse_db}'"
    ]

    connection {
      type        = "ssh"
      user        = var.ssh_username
      private_key = file(var.ssh_private_key_path)
      host        = self.network_interface[0].nat_ip_address
    }
  }

  # Provisioner 8: Node Exporter bootstrap
  provisioner "remote-exec" {
    inline = [
      "set -e",
      "sudo cloud-init status --wait",
      "sudo bash -lc 'printf \"ARGS=\\\"--web.listen-address=:${var.node_exporter_port}\\\"\\n\" > /etc/default/prometheus-node-exporter'",
      "sudo systemctl enable prometheus-node-exporter",
      "sudo systemctl restart prometheus-node-exporter"
    ]

    connection {
      type        = "ssh"
      user        = var.ssh_username
      private_key = file(var.ssh_private_key_path)
      host        = self.network_interface[0].nat_ip_address
    }
  }

  # Provisioner 9: nginx basic auth bootstrap
  provisioner "remote-exec" {
    inline = [
      "set -e",
      "sudo cloud-init status --wait",
      "sudo htpasswd -cb /etc/nginx/.htpasswd_reml '${var.basic_auth_username}' '${var.basic_auth_password}'",
      "sudo chmod 640 /etc/nginx/.htpasswd_reml",
      "sudo chown root:www-data /etc/nginx/.htpasswd_reml"
    ]

    connection {
      type        = "ssh"
      user        = var.ssh_username
      private_key = file(var.ssh_private_key_path)
      host        = self.network_interface[0].nat_ip_address
    }
  }

  # Provisioner 10: Remote execution (app setup)
  provisioner "remote-exec" {
    inline = [
      "set -e",
      "sudo cloud-init status --wait",

      # Install nginx configs
      "sudo cp /tmp/prefect.nginx.conf /etc/nginx/sites-available/prefect",
      "sudo cp /tmp/mlflow.nginx.conf /etc/nginx/sites-available/mlflow",
      "sudo ln -sf /etc/nginx/sites-available/prefect /etc/nginx/sites-enabled/",
      "sudo ln -sf /etc/nginx/sites-available/mlflow /etc/nginx/sites-enabled/",
      "sudo rm -f /etc/nginx/sites-enabled/default",
      "sudo nginx -t",
      "sudo systemctl reload nginx",

      # Install Prefect and MLflow
      "python3 -m venv /home/${var.ssh_username}/reml-env",
      "/home/${var.ssh_username}/reml-env/bin/pip install --upgrade pip",
      "/home/${var.ssh_username}/reml-env/bin/pip install prefect mlflow boto3",

      # Install systemd services
      "sudo cp /tmp/prefect.service /etc/systemd/system/prefect.service",
      "sudo cp /tmp/mlflow.service /etc/systemd/system/mlflow.service",
      "sudo systemctl daemon-reload",
      "sudo systemctl enable prefect mlflow",
      "sudo systemctl start prefect mlflow",

      # Obtain SSL certificates
      "sudo certbot --nginx -d prefect.reml.bpdu.ru -d mlflow.reml.bpdu.ru --non-interactive --agree-tos --email me@bpdu.ru --redirect",

      # Setup auto-renewal
      "sudo systemctl enable --now snap.certbot.renew.service",
      "sudo certbot renew --dry-run",

      # Configure Prefect API URL
      "/home/${var.ssh_username}/reml-env/bin/prefect config set PREFECT_API_URL=https://prefect.reml.bpdu.ru/api",

      # Cleanup
      "rm /tmp/*.nginx.conf /tmp/*.service",

      # Success flag
      "echo 'REML controller fully provisioned with SSL at $(date)' > /home/${var.ssh_username}/provision-status"
    ]

    connection {
      type        = "ssh"
      user        = var.ssh_username
      private_key = file(var.ssh_private_key_path)
      host        = self.network_interface[0].nat_ip_address
    }
  }
}

output "reml_controller_ip" {
  value = yandex_compute_instance.reml_controller.network_interface[0].nat_ip_address
}
