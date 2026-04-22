resource "yandex_vpc_security_group" "reml_controller" {
  name       = "reml-controller-sg"
  network_id = yandex_vpc_network.reml.id

  ingress {
    description    = "SSH from bastion"
    protocol       = "TCP"
    v4_cidr_blocks = [for ip in var.ssh_allowed_ips : "${ip}/32"]
    port           = 22
  }

  ingress {
    description    = "HTTP"
    protocol       = "TCP"
    v4_cidr_blocks = ["0.0.0.0/0"]
    port           = 80
  }

  ingress {
    description    = "HTTPS"
    protocol       = "TCP"
    v4_cidr_blocks = ["0.0.0.0/0"]
    port           = 443
  }

  ingress {
    description    = "Node Exporter from observability host"
    protocol       = "TCP"
    v4_cidr_blocks = ["${var.observability_allowed_ip}/32"]
    port           = var.node_exporter_port
  }

  egress {
    description    = "Allow all outbound traffic"
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
    from_port      = 0
    to_port        = 65535
  }
}
