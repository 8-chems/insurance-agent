from pydantic import BaseModel


class Evidence(BaseModel):
    source_id: str
    kind: str                    # "api" or "policy"
    title: str
    version: int | None = None
    section: str | None = None
    page: int | None = None
    retrieved_at: str
    data: dict
