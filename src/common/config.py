from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    project_id: str = ""
    region: str = "europe-west1"
    model_name: str = "set-AGENT_MODEL_NAME"
    verifier_model: str = "set-AGENT_VERIFIER_MODEL"
    claims_api_url: str = "http://localhost:9000"
    claims_api_token: str = ""
    sessions_db_url: str = ""
    allow_dev_tokens: bool = False      # LOCAL ONLY
    enable_graph: bool = False
    spanner_instance: str = ""
    spanner_database: str = ""
    model_config = {"env_prefix": "AGENT_"}


settings = Settings()
