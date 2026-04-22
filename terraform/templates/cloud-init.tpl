#cloud-config
package_update: true
package_upgrade: true

# Force SSH key setup
users:
  - name: ${ssh_username}
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys:
      - ${ssh_public_key}

packages:
  - docker.io
  - docker-compose
  - nginx
  - certbot
  - python3-certbot-nginx
  - postgresql
  - postgresql-contrib
  - prometheus-node-exporter
  - apache2-utils
  - snapd

runcmd:
  # Ensure SSH config is correct
  - sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
  - sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
  - systemctl restart sshd

  # Docker permissions
  - usermod -aG docker ${ssh_username}

  # Install Python and tools
  - apt install -y python3-venv python3-pip

  # Install certbot via snap
  - snap install --classic certbot
  - ln -s /snap/bin/certbot /usr/bin/certbot

  # Create directories for logs
  - mkdir -p /var/log/prefect /var/log/mlflow
  - chown ${ssh_username}:${ssh_username} /var/log/prefect /var/log/mlflow

  # Create MLflow artifacts directory
  - mkdir -p /home/${ssh_username}/mlflow_artifacts
  - chown ${ssh_username}:${ssh_username} /home/${ssh_username}/mlflow_artifacts

  # Create SSL directories
  - mkdir -p /etc/nginx/ssl /var/www/certbot

  # Start nginx
  - systemctl enable nginx
  - systemctl start nginx

  # Completion flag
  - echo "Cloud-init completed at $(date)" > /var/log/cloud-init-custom.log
