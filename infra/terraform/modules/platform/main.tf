data "google_project" "this" { project_id = var.project_id }

locals {
  apis = ["aiplatform", "run", "artifactregistry", "secretmanager", "bigquery", "storage", "pubsub",
    "firestore", "documentai", "spanner", "logging", "monitoring", "cloudtrace", "cloudbuild"]
  api_roles = ["roles/aiplatform.user", "roles/secretmanager.secretAccessor", "roles/bigquery.dataViewer",
  "roles/bigquery.jobUser", "roles/cloudtrace.agent"]
  ingest_roles = ["roles/aiplatform.user", "roles/bigquery.dataEditor", "roles/bigquery.jobUser",
  "roles/storage.objectViewer", "roles/documentai.apiUser", "roles/datastore.user"]
  pubsub_agent = "serviceAccount:service-${data.google_project.this.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
  graph_env = var.enable_graph ? {
    AGENT_ENABLE_GRAPH     = "true"
    AGENT_SPANNER_INSTANCE = "agent-graph"
    AGENT_SPANNER_DATABASE = "insurance-graph"
  } : {}
  common_env = {
    GOOGLE_GENAI_USE_VERTEXAI = "TRUE"
    GOOGLE_CLOUD_PROJECT      = var.project_id
    GOOGLE_CLOUD_LOCATION     = var.region
  }
}

resource "google_project_service" "apis" {
  for_each           = toset(local.apis)
  project            = var.project_id
  service            = "${each.value}.googleapis.com"
  disable_on_destroy = false
}

# ---------- identities ----------
resource "google_service_account" "api" {
  project    = var.project_id
  account_id = "api-sa"
  depends_on = [google_project_service.apis]
}
resource "google_service_account" "ingest" {
  project    = var.project_id
  account_id = "ingest-sa"
  depends_on = [google_project_service.apis]
}
resource "google_service_account" "pubsub_invoker" {
  project    = var.project_id
  account_id = "pubsub-invoker-sa"
  depends_on = [google_project_service.apis]
}
resource "google_project_iam_member" "api" {
  for_each = toset(local.api_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.api.email}"
}
resource "google_project_iam_member" "ingest" {
  for_each = toset(local.ingest_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.ingest.email}"
}

# ---------- registry and secrets ----------
resource "google_artifact_registry_repository" "agent" {
  project       = var.project_id
  location      = var.region
  repository_id = "agent"
  format        = "DOCKER"
  depends_on    = [google_project_service.apis]
}
resource "google_secret_manager_secret" "claims_token" {
  project   = var.project_id
  secret_id = "claims-token"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}
# placeholder so the first deploy can start; add the real token as a NEW version outside Terraform
resource "google_secret_manager_secret_version" "placeholder" {
  secret      = google_secret_manager_secret.claims_token.id
  secret_data = "REPLACE_ME"
  lifecycle { ignore_changes = [secret_data] }
}

# ---------- data ----------
resource "google_bigquery_dataset" "kb" {
  project    = var.project_id
  dataset_id = "kb"
  location   = var.region
  depends_on = [google_project_service.apis]
}
resource "google_bigquery_table" "chunks" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.kb.dataset_id
  table_id            = "chunks"
  deletion_protection = var.deletion_protection
  schema = jsonencode([
    { name = "chunk_id", type = "STRING" }, { name = "document_id", type = "STRING" },
    { name = "version", type = "INT64" }, { name = "effective_from", type = "DATE" },
    { name = "effective_to", type = "DATE" }, { name = "status", type = "STRING" },
    { name = "section", type = "STRING" }, { name = "page", type = "INT64" },
    { name = "source_uri", type = "STRING" }, { name = "text", type = "STRING" },
    { name = "embedding", type = "FLOAT64", mode = "REPEATED" },
    { name = "chunker_version", type = "STRING" }, { name = "embedding_model", type = "STRING" },
  ])
}
resource "google_storage_bucket" "policies" {
  project                     = var.project_id
  name                        = "${var.project_id}-policies"
  location                    = var.region
  uniform_bucket_level_access = true
  depends_on                  = [google_project_service.apis]
}
resource "google_firestore_database" "default" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
  depends_on  = [google_project_service.apis]
}

# ---------- events ----------
resource "google_pubsub_topic" "files" {
  project    = var.project_id
  name       = "policy-files"
  depends_on = [google_project_service.apis]
}
resource "google_pubsub_topic" "dlq" {
  project    = var.project_id
  name       = "policy-files-dlq"
  depends_on = [google_project_service.apis]
}
data "google_storage_project_service_account" "gcs" { project = var.project_id }
resource "google_pubsub_topic_iam_member" "gcs_publish" {
  topic  = google_pubsub_topic.files.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${data.google_storage_project_service_account.gcs.email_address}"
}
resource "google_storage_notification" "policies" {
  bucket             = google_storage_bucket.policies.name
  payload_format     = "JSON_API_V1"
  topic              = google_pubsub_topic.files.id
  event_types        = ["OBJECT_FINALIZE"]
  object_name_prefix = "policies/"
  depends_on         = [google_pubsub_topic_iam_member.gcs_publish]
}
resource "google_pubsub_subscription" "ingest" {
  project              = var.project_id
  name                 = "policy-ingest"
  topic                = google_pubsub_topic.files.id
  ack_deadline_seconds = 600
  push_config {
    push_endpoint = "${google_cloud_run_v2_service.ingest.uri}/pubsub"
    oidc_token { service_account_email = google_service_account.pubsub_invoker.email }
  }
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq.id
    max_delivery_attempts = 5
  }
}
resource "google_pubsub_subscription" "dlq_pull" {
  project = var.project_id
  name    = "policy-files-dlq-pull"
  topic   = google_pubsub_topic.dlq.id
}
resource "google_pubsub_topic_iam_member" "dlq_publish" {
  topic  = google_pubsub_topic.dlq.name
  role   = "roles/pubsub.publisher"
  member = local.pubsub_agent
}
resource "google_pubsub_subscription_iam_member" "dlq_subscribe" {
  subscription = google_pubsub_subscription.ingest.name
  role         = "roles/pubsub.subscriber"
  member       = local.pubsub_agent
}

# ---------- Cloud Run ----------
# The image is owned by the CI/CD pipeline, so Terraform ignores it (and traffic) after creation.
resource "google_cloud_run_v2_service" "api" {
  project  = var.project_id
  name     = "agent-api"
  location = var.region
  template {
    service_account = google_service_account.api.email
    scaling {
      min_instance_count = 0
      max_instance_count = var.max_instances
    }
    containers {
      image = var.api_image
      dynamic "env" {
        for_each = merge(local.common_env, local.graph_env)
        content {
          name  = env.key
          value = env.value
        }
      }
      env {
        name  = "AGENT_MODEL_NAME"
        value = var.model_name
      }
      env {
        name  = "AGENT_VERIFIER_MODEL"
        value = var.verifier_model
      }
      env {
        name = "AGENT_CLAIMS_API_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.claims_token.secret_id
            version = "latest"
          }
        }
      }
    }
  }
  lifecycle {
    ignore_changes = [template[0].containers[0].image, template[0].revision, traffic, client, client_version]
  }
  depends_on = [google_secret_manager_secret_version.placeholder, google_project_iam_member.api]
}
resource "google_cloud_run_v2_service_iam_member" "api_public" {
  count    = var.public_api ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service" "ingest" {
  project  = var.project_id
  name     = "rag-ingestion"
  location = var.region
  template {
    service_account = google_service_account.ingest.email
    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }
    containers {
      image = var.ingest_image
      resources {
        limits = { cpu = "2", memory = "2Gi" }
      }
      dynamic "env" {
        for_each = local.common_env
        content {
          name  = env.key
          value = env.value
        }
      }
      env {
        name  = "DOCAI_PROCESSOR"
        value = var.docai_processor
      }
    }
  }
  lifecycle {
    ignore_changes = [template[0].containers[0].image, template[0].revision, traffic, client, client_version]
  }
  depends_on = [google_project_iam_member.ingest]
}
resource "google_cloud_run_v2_service_iam_member" "ingest_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.ingest.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.pubsub_invoker.email}"
}

resource "google_cloud_run_v2_job" "batch" {
  project  = var.project_id
  name     = "rag-batch-ingestion"
  location = var.region
  template {
    task_count = 10
    template {
      service_account = google_service_account.ingest.email
      max_retries     = 2
      timeout         = "3600s"
      containers {
        image   = var.ingest_image
        command = ["python"]
        args    = ["-m", "src.ingestion.batch"]
        resources {
          limits = { cpu = "2", memory = "4Gi" }
        }
        dynamic "env" {
          for_each = local.common_env
          content {
            name  = env.key
            value = env.value
          }
        }
        env {
          name  = "SOURCE_BUCKET"
          value = google_storage_bucket.policies.name
        }
        env {
          name  = "DOCAI_PROCESSOR"
          value = var.docai_processor
        }
      }
    }
  }
  lifecycle {
    ignore_changes = [template[0].template[0].containers[0].image, client, client_version]
  }
}

# ---------- monitoring ----------
resource "google_logging_metric" "abstentions" {
  project = var.project_id
  name    = "abstentions"
  filter  = "jsonPayload.event=\"verification\" AND jsonPayload.status=\"abstained\""
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
  }
}

# ---------- graph (optional) ----------
# Edition and availability of Spanner Graph vary: confirm the edition you need in the Spanner documentation.
resource "google_spanner_instance" "graph" {
  count            = var.enable_graph ? 1 : 0
  project          = var.project_id
  name             = "agent-graph"
  display_name     = "Agent graph"
  config           = "regional-${var.region}"
  processing_units = var.graph_processing_units
  edition          = "ENTERPRISE"
  depends_on       = [google_project_service.apis]
}
# The schema (graph/schema.sql) is applied by a migration step, not by Terraform.
resource "google_spanner_database" "graph" {
  count               = var.enable_graph ? 1 : 0
  project             = var.project_id
  instance            = google_spanner_instance.graph[0].name
  name                = "insurance-graph"
  deletion_protection = var.deletion_protection
}
resource "google_spanner_database_iam_member" "api_reads" {
  count    = var.enable_graph ? 1 : 0
  project  = var.project_id
  instance = google_spanner_instance.graph[0].name
  database = google_spanner_database.graph[0].name
  role     = "roles/spanner.databaseReader"
  member   = "serviceAccount:${google_service_account.api.email}"
}
resource "google_spanner_database_iam_member" "sync_writes" {
  count    = var.enable_graph ? 1 : 0
  project  = var.project_id
  instance = google_spanner_instance.graph[0].name
  database = google_spanner_database.graph[0].name
  role     = "roles/spanner.databaseUser"
  member   = "serviceAccount:${google_service_account.ingest.email}"
}
