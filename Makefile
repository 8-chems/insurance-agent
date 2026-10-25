.PHONY: test lint run fake
test:
	pytest tests/unit -q
lint:
	ruff check src tests
fake:
	uvicorn tests.fake_claims:app --port 9000
run:
	uvicorn src.api.main:app --reload --port 8080
