output "private_dns" {
  value = {
    adg_service_discovery_dns = aws_service_discovery_private_dns_namespace.adg_services
    adg_service_discovery     = aws_service_discovery_service.adg_services
  }

  sensitive = true
}
