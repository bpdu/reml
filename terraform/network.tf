resource "yandex_vpc_network" "reml" {
  name = "reml-network"
}

resource "yandex_vpc_subnet" "reml_a" {
  name           = "reml-subnet-a"
  zone           = "ru-central1-a"
  network_id     = yandex_vpc_network.reml.id
  v4_cidr_blocks = ["10.10.10.0/24"]
}
