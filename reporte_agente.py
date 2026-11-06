"""Quality report for an ElevenAgents agent.

Pulls every finished conversation for one agent, reads the evaluation and
data-collection results ElevenLabs attached to it, and writes:
  - conversaciones.csv : one row per conversation
  - reporte.md         : pass rate per evaluation criterion

With --tests it also runs the agent's test suite and reports the results.

Setup:  pip install requests python-dotenv
        .env file with ELEVENLABS_API_KEY=... and AGENT_ID=...
Run:    python reporte_agente.py
        python reporte_agente.py --tests --repeat 3
"""
import argparse
import csv
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

BASE_URL = "https://api.elevenlabs.io"
TEST_PREFIX = "RF - "  # every test in the suite starts with this name prefix


class ElevenLabsAPI:
    def __init__(self, api_key):
        self.session = requests.Session()
        self.session.headers["xi-api-key"] = api_key

    def get(self, path, params=None):
        response = self.session.get(BASE_URL + path, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def post(self, path, body):
        response = self.session.post(BASE_URL + path, json=body, timeout=60)
        response.raise_for_status()
        return response.json()


def list_conversations(api, agent_id):
    """Yield every conversation summary for the agent, page by page."""
    params = {"agent_id": agent_id, "page_size": 100}
    while True:
        page = api.get("/v1/convai/conversations", params)
        yield from page.get("conversations", [])
        if not page.get("has_more"):
            break
        params["cursor"] = page["next_cursor"]


def conversation_rows(api, agent_id):
    """Fetch each finished conversation and flatten its analysis into one row."""
    rows = []
    for summary in list_conversations(api, agent_id):
        if summary.get("status") != "done":
            continue  # still running or being analyzed
        conv = api.get(f"/v1/convai/conversations/{summary['conversation_id']}")
        analysis = conv.get("analysis") or {}
        started = (conv.get("metadata") or {}).get("start_time_unix_secs")
        row = {
            "conversation_id": conv["conversation_id"],
            "start": datetime.fromtimestamp(started, timezone.utc).strftime("%Y-%m-%d %H:%M") if started else "",
            "duration_secs": (conv.get("metadata") or {}).get("call_duration_secs", ""),
            "call_successful": analysis.get("call_successful", ""),
        }
        for crit_id, res in (analysis.get("evaluation_criteria_results") or {}).items():
            row[f"eval:{crit_id}"] = res.get("result", "")
        for field_id, res in (analysis.get("data_collection_results") or {}).items():
            row[f"data:{field_id}"] = res.get("value", "")
        rows.append(row)
    return rows


def write_csv(rows, path):
    columns = []
    for row in rows:
        columns += [c for c in row if c not in columns]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def criteria_summary(rows):
    """Count success / failure / unknown per criterion."""
    counts = defaultdict(Counter)
    for row in rows:
        for column, value in row.items():
            if column.startswith("eval:") and value:
                counts[column[5:]][value] += 1
    return counts


def pass_rate(counter):
    judged = counter["success"] + counter["failure"]
    return f"{100 * counter['success'] / judged:.0f}%" if judged else "n/a"


def run_tests(api, agent_id, repeat):
    """Run every test whose name starts with TEST_PREFIX and wait for results."""
    tests = api.get("/v1/convai/agent-testing", {"search": TEST_PREFIX.strip(), "page_size": 100})["tests"]
    tests = [t for t in tests if t.get("entity_type", "test") == "test" and t["name"].startswith(TEST_PREFIX)]
    if not tests:
        print(f"No tests found whose name starts with '{TEST_PREFIX}'.")
        return []
    body = {"tests": [{"test_id": t["id"]} for t in tests], "repeat_count": repeat}
    started = api.post(f"/v1/convai/agents/{agent_id}/run-tests", body)
    invocation_id = started["test_runs"][0]["test_invocation_id"]
    print(f"Running {len(tests)} tests x{repeat}...")
    while True:
        result = api.get(f"/v1/convai/test-invocations/{invocation_id}")
        runs = result["test_runs"]
        if all(run["status"] != "pending" for run in runs):
            return runs
        time.sleep(5)


def tests_table(runs):
    by_test = defaultdict(Counter)
    for run in runs:
        by_test[run.get("test_name", "Unknown Test")][run["status"]] += 1
    lines = ["| Test | Passed | Failed |", "| --- | --- | --- |"]
    for name, c in sorted(by_test.items()):
        lines.append(f"| {name} | {c['passed']} | {c['failed'] + c['cancelled']} |")
    return lines


def main():
    parser = argparse.ArgumentParser(description="Quality report for an ElevenAgents agent")
    parser.add_argument("--tests", action="store_true", help="also run the test suite")
    parser.add_argument("--repeat", type=int, default=1, help="runs per test (2-20 for a pass rate)")
    args = parser.parse_args()

    load_dotenv()
    api = ElevenLabsAPI(os.environ["ELEVENLABS_API_KEY"])
    agent_id = os.environ["AGENT_ID"]

    rows = conversation_rows(api, agent_id)
    write_csv(rows, "conversaciones.csv")

    report = [f"# Quality report, {datetime.now():%Y-%m-%d}", "",
              f"Finished conversations analyzed: {len(rows)}", "",
              "| Criterion | Success | Failure | Unknown | Pass rate |",
              "| --- | --- | --- | --- | --- |"]
    for crit, c in sorted(criteria_summary(rows).items()):
        report.append(f"| {crit} | {c['success']} | {c['failure']} | {c['unknown']} | {pass_rate(c)} |")

    if args.tests:
        runs = run_tests(api, agent_id, args.repeat)
        if runs:
            report += ["", "## Test suite", ""] + tests_table(runs)

    with open("reporte.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")
    print("\n".join(report))
    print("\nWrote conversaciones.csv and reporte.md")


if __name__ == "__main__":
    main()
