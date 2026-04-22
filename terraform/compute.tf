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

  scheduling_policy {
    preemptible = true
  }

  resources {
    cores  = 2
    memory = 4
  }

  boot_disk {
    initialize_params {
      image_id = data.yandex_compute_image.ubuntu.image_id
      size     = 30
      type     = "network-hdd"
    }
  }

  network_interface {
    subnet_id      = yandex_vpc_subnet.reml_a.id
    nat            = true
    nat_ip_address = yandex_vpc_address.reml_static.external_ipv4_address[0].address
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
    source      = "${path.module}/templates/prefect.nginx.tpl"
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
    source      = "${path.module}/templates/mlflow.nginx.tpl"
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

  # Provisioner 5: Remote execution (setup)
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
