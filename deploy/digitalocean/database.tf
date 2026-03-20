# Terraform configuration for DigitalOcean PostgreSQL
# Usage:
#   terraform init
#   terraform plan
#   terraform apply

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.30"
    }
  }
}

variable "do_token" {
  description = "DigitalOcean API Token"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "DigitalOcean Region"
  type        = string
  default     = "nyc1"
}

variable "database_size" {
  description = "Database size (db-s-1vcpu-1gb or larger)"
  type        = string
  default     = "db-s-1vcpu-1gb"
}

provider "digitalocean" {
  token = var.do_token
}

# PostgreSQL Database Cluster
resource "digitalocean_database_cluster" "postgres" {
  name       = "rtl-gen-db"
  engine     = "pg"
  version    = "15"
  size       = var.database_size
  region     = var.region
  node_count = 1
  
  tags = ["rtl-gen-ai", "production"]
}

# Database
resource "digitalocean_database_db" "database" {
  cluster_id = digitalocean_database_cluster.postgres.id
  name       = "rtlgen"
}

# Database user
resource "digitalocean_database_user" "app_user" {
  cluster_id = digitalocean_database_cluster.postgres.id
  name       = "rtl_app"
}

# Firewall rule for app
resource "digitalocean_database_firewall" "app_firewall" {
  cluster_id = digitalocean_database_cluster.postgres.id
  
  rule {
    type  = "app"
    value = "web"  # References the app config
  }
}

# Outputs
output "database_host" {
  description = "Database hostname"
  value       = digitalocean_database_cluster.postgres.host
}

output "database_port" {
  description = "Database port"
  value       = digitalocean_database_cluster.postgres.port
}

output "database_user" {
  description = "Database username"
  value       = digitalocean_database_user.app_user.name
}

output "database_password" {
  description = "Database password"
  value       = digitalocean_database_user.app_user.password
  sensitive   = true
}

output "database_url" {
  description = "Complete database connection URL"
  value       = "postgresql://${digitalocean_database_user.app_user.name}:${digitalocean_database_user.app_user.password}@${digitalocean_database_cluster.postgres.host}:${digitalocean_database_cluster.postgres.port}/${digitalocean_database_db.database.name}?sslmode=require"
  sensitive   = true
}

output "cluster_urn" {
  description = "Database cluster URN"
  value       = digitalocean_database_cluster.postgres.urn
}
