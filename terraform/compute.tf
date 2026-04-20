data "yandex_compute_image" "ubuntu" {
  family = "ubuntu-2404-lts"
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
    ssh-keys = "ubuntu:${file("~/.ssh/reml.pub")}"
  }
}

output "reml_cpu_ip" {
  value = yandex_compute_instance.reml_controller.network_interface.0.nat_ip_address
}
