"""Run the golden set against a deployed URL. Exit code 1 if any threshold fails.
Usage: python evals/run_eval.py https://canary---agent-api-xxxx.a.run.app
Env: GCP_ID_TOKEN (optional Google identity token for private Cloud Run services)."""
import json
import os
import statistics as st
import sys

import httpx
import yaml


def ask(url, token, q):
    h = {"Authorization": f"Bearer {token}"}
    if os.environ.get("GCP_ID_TOKEN"):               # Cloud Run reads this header for IAM auth
        h["X-Serverless-Authorization"] = f"Bearer {os.environ['GCP_ID_TOKEN']}"
    r = httpx.post(f"{url}/api/v1/chat", headers=h, json={"message": q}, timeout=90)
    r.raise_for_status()
    return r.json()


def run(url, tokens, path="evals/golden_set.jsonl"):
    results = []
    for line in open(path, encoding="utf-8"):
        c = json.loads(line)
        out = ask(url, tokens[c["user"]], c["question"])
        t = out["answer"].lower()
        results.append({
            "contains_ok": all(k.lower() in t for k in c.get("must_contain", [])),
            "forbidden_ok": not any(k.lower() in t for k in c.get("must_not_contain", [])),
            "abstain_ok": (out["status"] == "abstained") == c["must_abstain"],
            "cited_ok": c["must_abstain"] or bool(out["sources"])})
    return {k: st.mean(r[k] for r in results) for k in results[0]}


if __name__ == "__main__":
    scores = run(sys.argv[1], json.load(open("evals/test_tokens.json", encoding="utf-8")))
    thr = yaml.safe_load(open("evals/thresholds.yaml", encoding="utf-8"))
    print(scores)
    bad = {k: v for k, v in scores.items() if v < thr[k]["min"]}
    if bad:
        print("FAILED thresholds:", bad)
    sys.exit(1 if bad else 0)
