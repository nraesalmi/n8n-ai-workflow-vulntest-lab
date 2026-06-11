#!/usr/bin/env python3
"""
Transform n8n workflow JSONs from Telegram/Chat/Webhook triggers to file-based I/O.

For each workflow:
  - Replaces Chat/Webhook triggers with Manual Trigger + "Read Input from File" Code node
  - For Manual-only workflows: injects Read Input after the Manual Trigger
  - Injects "Write Output to File" Code node before Log Execution Metadata
  - Updates Log node expressions to reference the new input node
  - Adds file I/O sticky notes
"""

import json, os, glob, re
from uuid import uuid4

WORKFLOW_DIRS = [
    "n8n/workflows/baseline",
    "n8n/workflows/basic_guardrail",
    "n8n/workflows/custom_guardrail",
]

READ_INPUT_CODE = """const fs = require('fs');
const path = '/data/inputs/current_payload.json';
let inputData;
try {
  const raw = fs.readFileSync(path, 'utf8');
  inputData = JSON.parse(raw);
} catch(e) {
  inputData = { payload: '', payload_id: 'unknown' };
}
const payload = inputData.payload || '';
return [{
  json: {
    payload: payload,
    payload_id: inputData.payload_id || 'unknown',
    workflow_id: inputData.workflow_id || 'unknown',
    chatInput: payload,
    transform_request: payload,
    query: payload,
    user_input: payload,
    body: { user_input: payload, transform_request: payload, query: payload },
    turn_number: inputData.turn_number || 1,
    metadata: inputData.metadata || {}
  }
}];"""

WRITE_OUTPUT_CODE = """const fs = require('fs');
const path = require('path');
const outputDir = '/data/outputs';
fs.mkdirSync(outputDir, { recursive: true });
const input = $input.first().json;
const ts = new Date().toISOString().replace(/[:.]/g, '-');
const safeName = ($workflow.name || 'unknown').replace(/[^a-zA-Z0-9_-]/g, '_');
const filename = safeName + '_' + ts + '.json';
const output = {
  timestamp: new Date().toISOString(),
  workflow_name: $workflow.name,
  payload_id: input.payload_id || 'unknown',
  attack_success: 'MANUAL_REVIEW_REQUIRED',
  agent_output: input.output || input.agent_output || '',
  tools_called: input.tool_calls || [],
  guardrail_triggered: input.guardrail_triggered || null,
  raw_output: input
};
fs.writeFileSync(path.join(outputDir, filename), JSON.stringify(output, null, 2));
return [{ json: { ...input, output_written: filename } }];"""


def node_id():
    return str(uuid4())


def make_manual_trigger():
    return {
        "id": node_id(),
        "name": "Manual Trigger",
        "type": "n8n-nodes-base.manualTrigger",
        "typeVersion": 1,
        "position": [250, 300],
        "parameters": {}
    }


def make_read_input_node(pos_x=480, pos_y=300):
    return {
        "id": node_id(),
        "name": "Read Input from File",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [pos_x, pos_y],
        "parameters": {"jsCode": READ_INPUT_CODE}
    }


def make_write_output_node(pos_x=1200, pos_y=300):
    return {
        "id": node_id(),
        "name": "Write Output to File",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [pos_x, pos_y],
        "parameters": {"jsCode": WRITE_OUTPUT_CODE}
    }


def make_file_io_note(pos_x=50, pos_y=420):
    return {
        "id": node_id(),
        "name": "File I/O Note",
        "type": "n8n-nodes-base.stickyNote",
        "typeVersion": 1,
        "position": [pos_x, pos_y],
        "parameters": {
            "content": (
                "=== FILE-BASED I/O ===\n\n"
                "INPUT:  Place a payload JSON in /data/inputs/current_payload.json\n"
                "        (mounted from n8n/inputs/)\n\n"
                "OUTPUT: Results written to /data/outputs/<workflow>_<timestamp>.json\n"
                "        (mounted from n8n/outputs/)\n\n"
                "Input format:\n"
                "{\n"
                '  "payload": "attack string here",\n'
                '  "payload_id": "01-01",\n'
                '  "workflow_id": "wf_01",\n'
                '  "turn_number": 1\n'
                "}\n\n"
                "Run: Click Execute Workflow (Manual Trigger)."
            ),
            "height": 300,
            "width": 380
        }
    }


def find_log_node(wf):
    for n in wf["nodes"]:
        if n["type"] == "n8n-nodes-base.set" and "Log" in n.get("name", ""):
            return n
    return None


def rewrite_log_expression(wf, old_name, new_name="Read Input from File"):
    """Search workflow for Log node and update trigger reference."""
    for n in wf["nodes"]:
        if n["type"] != "n8n-nodes-base.set" or "Log" not in n.get("name", ""):
            continue
        for a in n.get("parameters", {}).get("assignments", {}).get("assignments", []):
            val = a.get("value", "")
            if not isinstance(val, str):
                continue
            if old_name in val:
                a["value"] = val.replace(f"$('{old_name}')", f"$('{new_name}')")
                if a["value"] == val:  # try double-quoted variant if single-quoted didn't match
                    a["value"] = val.replace(f'$("{old_name}")', f'$("{new_name}")')


def update_sticky_notes(wf):
    for n in wf["nodes"]:
        if n["type"] != "n8n-nodes-base.stickyNote":
            continue
        c = n["parameters"].get("content", "")
        c = c.replace("POST to /webhook/", "Set payload in input file for ")
        c = c.replace("POST /webhook/", "Set payload in input file for ")
        c = c.replace(" (POST to /webhook/", " (via input file ")
        c = re.sub(
            r"POST JSON to `http://localhost:5678/webhook/[^`]+`",
            "Place payload JSON in n8n/inputs/current_payload.json",
            c
        )
        n["parameters"]["content"] = c


def clean_stale_connections(connections, valid_names):
    """Remove connections to/from nodes not in valid_names."""
    result = {}
    for src, src_conns in connections.items():
        if src not in valid_names:
            continue
        cleaned = {}
        for conn_type, conn_list in src_conns.items():
            cleaned_list = []
            for alt_list in conn_list:
                cleaned_alt = [c for c in alt_list if c.get("node") in valid_names]
                if cleaned_alt:
                    cleaned_list.append(cleaned_alt)
            if cleaned_list:
                cleaned[conn_type] = cleaned_list
        if cleaned:
            result[src] = cleaned
    return result


def insert_write_output_before_log(connections, log_node):
    """Rewire so the node feeding into Log instead feeds Write Output → Log."""
    if not log_node:
        return connections, False

    log_name = log_node["name"]
    modified = False
    for src_name, src_conns in list(connections.items()):
        for conn_type, conn_list in src_conns.items():
            for alt_list in conn_list:
                for conn in alt_list:
                    if conn.get("node") == log_name:
                        conn["node"] = "Write Output to File"
                        connections.setdefault("Write Output to File", {}).setdefault("main", []).append(
                            [{"node": log_name, "type": "main", "index": 0}]
                        )
                        modified = True
    return connections, modified


def replace_trigger_with_file_io(wf, old_trigger, log_node, filepath):
    """Replace a Chat/Webhook trigger with Manual Trigger → Read Input."""
    nodes = wf["nodes"]
    connections = wf.get("connections", {})

    old_name = old_trigger["name"]
    outgoing = connections.get(old_name, {})
    tx, ty = old_trigger.get("position", [250, 300])

    # Build new nodes
    manual_node = make_manual_trigger()
    manual_node["position"] = [tx, ty]

    read_node = make_read_input_node(tx + 230, ty)
    write_node = make_write_output_node(
        (log_node.get("position", [1200, 300])[0] - 250) if log_node else (tx + 500),
        ty
    )
    note = make_file_io_note(tx, ty + 250)

    # Build connection map
    new_conns = {}
    for src, sc in connections.items():
        if src != old_name:
            new_conns[src] = sc

    # Manual Trigger → Read Input
    new_conns["Manual Trigger"] = {
        "main": [[{"node": "Read Input from File", "type": "main", "index": 0}]]
    }

    # Read Input → old trigger's downstreams
    if outgoing:
        new_conns["Read Input from File"] = outgoing

    # Insert Write Output before Log
    new_conns, _ = insert_write_output_before_log(new_conns, log_node)

    # Update Log expression
    rewrite_log_expression(wf, old_name)

    # Remove old trigger, add new nodes
    kept = [n for n in nodes if n["id"] != old_trigger["id"]]
    kept.extend([manual_node, read_node, write_node, note])

    # Clean up
    valid = {n["name"] for n in kept}
    new_conns = clean_stale_connections(new_conns, valid)
    update_sticky_notes(wf)
    for n in kept:
        n.pop("webhookId", None)

    wf["nodes"] = kept
    wf["connections"] = new_conns

    with open(filepath, 'w') as f:
        json.dump(wf, f, indent=2)

    print(f"  [OK] {os.path.basename(filepath)} — replaced '{old_name}' → file I/O")


def inject_after_existing_manual(wf, manual_node, log_node, filepath):
    """Inject Read Input after an existing Manual Trigger + Write Output before Log."""
    nodes = wf["nodes"]
    connections = wf.get("connections", {})

    mt_name = manual_node["name"]
    outgoing = connections.get(mt_name, {})
    tx, ty = manual_node.get("position", [250, 300])

    read_node = make_read_input_node(tx + 230, ty)
    write_node = make_write_output_node(
        (log_node.get("position", [1200, 300])[0] - 250) if log_node else (tx + 500),
        ty
    )
    note = make_file_io_note(tx, ty + 250)

    nodes.extend([read_node, write_node, note])

    # Rewire: Manual → Read Input → (old downstream)
    new_conns = {}
    for src, sc in connections.items():
        if src == mt_name:
            new_conns[mt_name] = {
                "main": [[{"node": "Read Input from File", "type": "main", "index": 0}]]
            }
            if outgoing:
                new_conns["Read Input from File"] = outgoing
        else:
            new_conns[src] = sc

    new_conns, _ = insert_write_output_before_log(new_conns, log_node)

    rewrite_log_expression(wf, mt_name)

    valid = {n["name"] for n in nodes}
    new_conns = clean_stale_connections(new_conns, valid)
    update_sticky_notes(wf)
    for n in nodes:
        n.pop("webhookId", None)

    wf["connections"] = new_conns

    with open(filepath, 'w') as f:
        json.dump(wf, f, indent=2)

    print(f"  [OK] {os.path.basename(filepath)} — injected file I/O after Manual Trigger '{mt_name}'")


def transform_workflow(filepath):
    with open(filepath) as f:
        wf = json.load(f)

    nodes = wf["nodes"]

    chat_webhook = [
        n for n in nodes
        if n["type"] in ("@n8n/n8n-nodes-langchain.chatTrigger", "n8n-nodes-base.webhook")
    ]
    manual_triggers = [n for n in nodes if n["type"] == "n8n-nodes-base.manualTrigger"]
    log_node = find_log_node(wf)

    # Custom security node — skip
    if "custom_security_node" in filepath:
        print(f"  [SKIP] Custom security node scaffold")
        return

    if chat_webhook:
        # wf_08 special handling: Phase B trigger is the one to replace
        is_wf08 = "wf_08" in filepath or "WF-08" in wf.get("name", "")
        if is_wf08:
            # Find the Chat trigger (Phase B) — that's the one to replace
            phase_b_chat = [n for n in chat_webhook if "Phase B" in n.get("name", "")]
            old = phase_b_chat[0] if phase_b_chat else chat_webhook[0]
        else:
            old = chat_webhook[0]
        replace_trigger_with_file_io(wf, old, log_node, filepath)
    elif manual_triggers:
        inject_after_existing_manual(wf, manual_triggers[0], log_node, filepath)
    else:
        print(f"  [WARN] No trigger nodes found in {os.path.basename(filepath)}")


def main():
    project_root = os.path.join(os.path.dirname(__file__), "..")
    count = 0
    for rel_dir in WORKFLOW_DIRS:
        abs_dir = os.path.join(project_root, rel_dir)
        if not os.path.isdir(abs_dir):
            continue
        for fpath in sorted(glob.glob(os.path.join(abs_dir, "*.json"))):
            print(f"Processing: {os.path.relpath(fpath, project_root)}")
            try:
                transform_workflow(fpath)
                count += 1
            except Exception as e:
                import traceback
                print(f"  [FAIL] {e}")
                traceback.print_exc()
    print(f"\nDone. Processed {count} files.")


if __name__ == "__main__":
    main()
