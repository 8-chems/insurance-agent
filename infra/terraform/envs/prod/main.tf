terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.30"
    }
  }
  backend "gcs" {} # bucket and prefix are passed with -backend-config in CI
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" { type = string }
variable "region" {
  type    = string
  default = "europe-west1"
}
variable "model_name" { type = string }
variable "verifier_model" { type = string }
variable "docai_processor" {
  type    = string
  default = ""
}

variable "enable_graph" {
  type    = bool
  default = false
}

module "platform" {
  source              = "../../modules/platform"
  project_id          = var.project_id
  region              = var.region
  env                 = "prod"
  model_name          = var.model_name
  verifier_model      = var.verifier_model
  docai_processor     = var.docai_processor
  enable_graph        = var.enable_graph
  public_api          = false
  deletion_protection = true
}

output "api_url" { value = module.platform.api_url }
output "registry" { value = module.platform.registry }
