#!/usr/bin/env python3
"""
Batch experiment runner for n8n file-based I/O workflows.

Reads payloads from test_payloads.json, writes each to the shared input file,
triggers the corresponding n8n workflow via API, and collects output files.

Usage:
  # Run all payloads for workflow wf_01 across all configurations
  python scripts/batch_runner.py --workflow wf_01

  # Run a specific payload across all configurations
  python scripts/batch_runner.py --workflow wf_01 --payload 01-01

  # Run all workflows (baseline only, 30 runs each)
  python scripts/batch_runner.py --all --runs 30 --variants baseline

  # Run with custom n8n URL and optional API key
  python scripts/batch_runner.py --workflow wf_01 --n8n-url http://localhost:5678 --api-key ''
"""

import argparse
import json
import os
import subprocess
import sys
import time
import csv
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_ROOT / "n8n" / "inputs" / "current_payload.json"
OUTPUT_DIR = PROJECT_ROOT / "n8n" / "outputs"
TEST_PAYLOADS_FILE = PROJECT_ROOT / "n8n" / "workflows" / "test_payloads.json"
EXPERIMENT_CONFIG = PROJECT_ROOT / "n8n" / "workflows" / "experiment_run_config.json"

# Maps workflow IDs to n8n workflow names (as stored in n8n after import)
# The names match the "name" field in the workflow JSON files.
WORKFLOW_NAMES = {
    "wf_01": "WF-01: Direct Prompt Injection via Chat Input",
    "wf_02": "WF-02: Indirect Injection via Web Scrape",
    "wf_03": "WF-03: Indirect Injection via Email/Database Row",
    "wf_04": "WF-04: Insecure Output Handling -> Code Node Execution",
    "wf_05": "WF-05: Excessive Agency / Unauthorized Tool Invocation",
    "wf_06": "WF-06: Credential / Secret Exfiltration",
    "wf_07": "WF-07: System Prompt Extraction",
    "wf_08": "WF-08: Memory / Vector Store Poisoning",
    "wf_09": "WF-09: Agent Loop / Unbounded Resource Consumption",
    "wf_10": "WF-10: Multi-hop Trust Boundary Escalation",
}

WORKFLOW_FILES = {
    "wf_01": {"baseline": "wf_01_direct_injection_baseline.json", "guardrail": "wf_01_direct_injection_guardrail.json"},
    "wf_02": {"baseline": "wf_02_indirect_webscrape_baseline.json", "guardrail": "wf_02_indirect_webscrape_guardrail.json"},
    "wf_03": {"baseline": "wf_03_indirect_email_db_baseline.json", "guardrail": "wf_03_indirect_email_db_guardrail.json"},
    "wf_04": {"baseline": "wf_04_code_execution_baseline.json", "guardrail": "wf_04_code_execution_guardrail.json"},
    "wf_05": {"baseline": "wf_05_excessive_agency_baseline.json", "guardrail": "wf_05_excessive_agency_guardrail.json"},
    "wf_06": {"baseline": "wf_06_credential_exfiltration_baseline.json", "guardrail": "wf_06_credential_exfiltration_guardrail.json"},
    "wf_07": {"baseline": "wf_07_system_prompt_extraction_baseline.json", "guardrail": "wf_07_system_prompt_extraction_guardrail.json"},
    "wf_08": {"baseline": "wf_08_vector_store_poisoning_baseline.json", "guardrail": "wf_08_vector_store_poisoning_guardrail.json"},
    "wf_09": {"baseline": "wf_09_agent_loop_baseline.json", "guardrail": "wf_09_agent_loop_guardrail.json"},
    "wf_10": {"baseline": "wf_10_multihop_trust_escalation_baseline.json", "guardrail": "wf_10_multihop_trust_escalation_guardrail.json"},
}


class N8nClient:
    """Minimal n8n REST API client for triggering workflows and checking executions."""

    def __init__(self, base_url="http://localhost:5678", api_key=None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if api_key:
            self.session.headers["X-N8N-API-KEY"] = api_key

    def get_workflows(self):
        """List all workflows. Returns list of {id, name, active}."""
        resp = self.session.get(urljoin(self.base_url, "/rest/workflows"))
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])

    def find_workflow_id(self, name_pattern):
        """Find workflow ID by name pattern (case-insensitive substring match)."""
        workflows = self.get_workflows()
        for wf in workflows:
            if name_pattern.lower() in wf["name"].lower():
                return wf["id"]
        return None

    def execute_workflow(self, workflow_id):
        """Trigger a manual execution of a workflow. Returns execution ID."""
        resp = self.session.post(
            urljoin(self.base_url, f"/rest/workflows/{workflow_id}/execute"),
            json={}
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("executionId")

    def get_execution(self, execution_id):
        """Get execution status and data."""
        resp = self.session.get(
            urljoin(self.base_url, f"/rest/executions/{execution_id}")
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {})

    def wait_for_execution(self, execution_id, timeout=120, poll_interval=2):
        """Poll until execution finishes. Returns execution data."""
        start = time.time()
        while time.time() - start < timeout:
            exec_data = self.get_execution(execution_id)
            status = exec_data.get("status")
            if status in ("success", "error", "crashed", "waiting"):
                return exec_data
            time.sleep(poll_interval)
        raise TimeoutError(f"Execution {execution_id} did not complete within {timeout}s")


def write_input_payload(payload_entry, workflow_id):
    """Write a payload entry to the shared input file."""
    payload_data = {
        "payload": payload_entry["payload"],
        "payload_id": payload_entry["id"],
        "workflow_id": workflow_id,
        "turn_number": 1,
        "metadata": {
            "attack_type": payload_entry.get("technique", "unknown"),
            "severity": payload_entry.get("severity", "medium"),
            "technique": payload_entry.get("technique", "unknown"),
        }
    }
    with open(INPUT_FILE, "w") as f:
        json.dump(payload_data, f, indent=2)
    return payload_data


def read_output_files(since_timestamp=None):
    """Read all output files from the output directory, newest first."""
    outputs = []
    for f in sorted(OUTPUT_DIR.glob("*.json"), key=os.path.getmtime, reverse=True):
        with open(f) as fh:
            try:
                data = json.load(fh)
                outputs.append(data)
            except json.JSONDecodeError:
                continue
    return outputs


def get_latest_output():
    """Get the most recent output file."""
    files = sorted(OUTPUT_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)
    if not files:
        return None
    with open(files[0]) as f:
        return json.load(f)


def run_single_experiment(n8n, workflow_id, payload_entry, variant="baseline", runs=1):
    """Run a single experiment: write payload, trigger workflow, collect output."""
    wf_name = WORKFLOW_NAMES.get(workflow_id, workflow_id)
    payload_info = write_input_payload(payload_entry, workflow_id)

    print(f"  Payload: {payload_entry['id']} ({payload_entry.get('technique', 'unknown')})")
    print(f"  Variant: {variant} | Runs: {runs}")

    results = []
    for run_idx in range(runs):
        # Find workflow in n8n
        n8n_wf_id = n8n.find_workflow_id(wf_name[:40])  # first 40 chars should be unique
        if not n8n_wf_id:
            # Try the variant-specific name
            variant_name = f"{wf_name} ({variant})"
            n8n_wf_id = n8n.find_workflow_id(wf_name[:30])
            if not n8n_wf_id:
                print(f"    [SKIP] Workflow '{wf_name}' not found in n8n. Import it first.")
                print(f"    To import: docker exec n8n-app n8n import:workflow --input=/tmp/workflows/{variant}/{WORKFLOW_FILES[workflow_id][variant]}")
                return []

        # Trigger execution
        try:
            exec_id = n8n.execute_workflow(n8n_wf_id)
            print(f"    Run {run_idx + 1}/{runs}: execution {exec_id}...", end=" ", flush=True)
        except Exception as e:
            print(f"FAILED to trigger: {e}")
            continue

        # Wait for completion
        try:
            exec_data = n8n.wait_for_execution(exec_id, timeout=120)
            status = exec_data.get("status", "unknown")
            print(f"status={status}")

            # Read the latest output file
            output = get_latest_output()
            result = {
                "run_id": run_idx + 1,
                "payload_id": payload_entry["id"],
                "workflow_id": workflow_id,
                "variant": variant,
                "execution_id": exec_id,
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "attack_success": output.get("attack_success", "MANUAL_REVIEW_REQUIRED") if output else "NO_OUTPUT",
                "agent_output": output.get("agent_output", "") if output else "",
                "output_file": list(OUTPUT_DIR.glob("*.json"))[0].name if list(OUTPUT_DIR.glob("*.json")) else None,
            }
            results.append(result)

        except Exception as e:
            print(f"TIMEOUT/ERROR: {e}")
            results.append({
                "run_id": run_idx + 1,
                "payload_id": payload_entry["id"],
                "workflow_id": workflow_id,
                "variant": variant,
                "execution_id": exec_id,
                "status": "timeout",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "attack_success": "ERROR",
                "agent_output": str(e),
            })

    return results


def save_results(results, workflow_id, variant):
    """Save experiment results to a CSV log file."""
    log_dir = PROJECT_ROOT / "experiment_logs"
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{workflow_id}_{variant}_{timestamp}.csv"

    if not results:
        print(f"  No results to save.")
        return

    fieldnames = [
        "run_id", "payload_id", "workflow_id", "variant",
        "execution_id", "status", "timestamp",
        "attack_success", "agent_output", "output_file"
    ]

    with open(log_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"  Results saved to: {log_file}")


def load_payloads():
    """Load all test payloads from test_payloads.json."""
    if not TEST_PAYLOADS_FILE.exists():
        print(f"ERROR: {TEST_PAYLOADS_FILE} not found.")
        sys.exit(1)

    with open(TEST_PAYLOADS_FILE) as f:
        data = json.load(f)

    return {k: v for k, v in data.items() if k.startswith("wf_")}


def main():
    parser = argparse.ArgumentParser(
        description="n8n Security Research Batch Experiment Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--workflow", choices=list(WORKFLOW_NAMES.keys()) + ["all"],
                        default="all", help="Workflow ID to run")
    parser.add_argument("--payload", help="Specific payload ID (e.g., 01-01). Runs all if omitted.")
    parser.add_argument("--variants", nargs="+", choices=["baseline", "guardrail"],
                        default=["baseline", "guardrail"], help="Which variants to test")
    parser.add_argument("--runs", type=int, default=1, help="Number of runs per payload")
    parser.add_argument("--n8n-url", default="http://localhost:5678", help="n8n base URL")
    parser.add_argument("--api-key", default="", help="n8n API key (if auth enabled)")
    parser.add_argument("--all", action="store_true", help="Run all workflows")
    args = parser.parse_args()

    # Ensure input file exists
    if not INPUT_FILE.parent.exists():
        INPUT_FILE.parent.mkdir(parents=True)

    # Ensure output dir exists
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Connect to n8n
    print(f"Connecting to n8n at {args.n8n_url}...")
    n8n = N8nClient(base_url=args.n8n_url, api_key=args.api_key)

    # Verify connection
    try:
        workflows = n8n.get_workflows()
        print(f"  Found {len(workflows)} workflows in n8n.")
        for w in workflows:
            print(f"    - {w['name']} (id={w['id']}, active={w['active']})")
    except Exception as e:
        print(f"  ERROR: Cannot connect to n8n: {e}")
        print(f"  Make sure n8n is running and accessible at {args.n8n_url}")
        sys.exit(1)

    # Load payloads
    all_payloads = load_payloads()

    if args.workflow == "all":
        workflow_ids = list(WORKFLOW_NAMES.keys())
    else:
        workflow_ids = [args.workflow]

    total_runs = 0
    for wf_id in workflow_ids:
        if wf_id not in all_payloads:
            print(f"\n[{wf_id}] No payloads found in test_payloads.json, skipping.")
            continue

        payloads = all_payloads[wf_id]["payloads"]
        if args.payload:
            payloads = [p for p in payloads if p["id"] == args.payload]
            if not payloads:
                print(f"\n[{wf_id}] Payload '{args.payload}' not found.")
                continue

        print(f"\n{'='*60}")
        print(f"  Workflow: {WORKFLOW_NAMES[wf_id]} ({wf_id})")
        print(f"  Attack:   {all_payloads[wf_id].get('attack_type', 'N/A')}")
        print(f"  OWASP:    {all_payloads[wf_id].get('owasp_category', 'N/A')}")
        print(f"  Payloads: {len(payloads)} | Runs each: {args.runs}")
        print(f"{'='*60}")

        for variant in args.variants:
            print(f"\n  --- Variant: {variant} ---")
            for payload in payloads:
                results = run_single_experiment(
                    n8n, wf_id, payload, variant=variant, runs=args.runs
                )
                total_runs += len(results)
                save_results(results, wf_id, variant)

    print(f"\n{'='*60}")
    print(f"  Complete! Total runs: {total_runs}")
    print(f"  Results in: experiment_logs/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
