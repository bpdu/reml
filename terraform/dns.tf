resource "yandex_dns_zone" "reml" {
  name        = "reml-zone"
  zone        = "reml.bpdu.ru."
  public      = true
  description = "DNS zone for REML project"
}

resource "yandex_dns_recordset" "prefect" {
  zone_id = yandex_dns_zone.reml.id
  name    = "prefect.reml.bpdu.ru."
  type    = "A"
  ttl     = 300
  data    = [yandex_vpc_address.reml_static.external_ipv4_address[0].address]
}

resource "yandex_dns_recordset" "mlflow" {
  zone_id = yandex_dns_zone.reml.id
  name    = "mlflow.reml.bpdu.ru."
  type    = "A"
  ttl     = 300
  data    = [yandex_vpc_address.reml_static.external_ipv4_address[0].address]
}

resource "yandex_dns_recordset" "reml_controller" {
  zone_id = yandex_dns_zone.reml.id
  name    = "controller.reml.bpdu.ru."
  type    = "A"
  ttl     = 300
  data    = [yandex_vpc_address.reml_static.external_ipv4_address[0].address]
}
