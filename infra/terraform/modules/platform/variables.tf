variable "project_id" { type = string }
variable "region" {
  type    = string
  default = "europe-west1"
}
variable "env" { type = string }
variable "model_name" { type = string }
variable "verifier_model" { type = string }
variable "docai_processor" {
  type    = string
  default = ""
}
variable "api_image" {
  type    = string
  default = "us-docker.pkg.dev/cloudrun/container/hello"
}
variable "ingest_image" {
  type    = string
  default = "us-docker.pkg.dev/cloudrun/container/hello"
}
variable "max_instances" {
  type    = number
  default = 10
}
variable "public_api" {
  type    = bool
  default = false
}
variable "enable_graph" {
  type    = bool
  default = false
}
variable "graph_processing_units" {
  type    = number
  default = 1000
}
variable "deletion_protection" {
  type    = bool
  default = true
}
