#!/usr/bin/env python3
"""
Patch all workflow JSON files to add configurable LLM backend support.
- Adds baseURL option to all lmChatOpenAi nodes (reads from env LLM_BASE_URL)
- Adds model parameter override via LLM_MODEL env var expression
"""
import json
import glob
import os

WORKFLOW_DIRS = [
    '../n8n/workflows/baseline',
    '../n8n/workflows/basic_guardrail',
    '../n8n/workflows/custom_guardrail',
]

CHAT_MODEL_TYPE = '@n8n/n8n-nodes-langchain.lmChatOpenAi'


def patch_file(filepath):
    with open(filepath) as f:
        wf = json.load(f)

    modified = False
    for node in wf.get('nodes', []):
        if node.get('type') != CHAT_MODEL_TYPE:
            continue

        params = node.setdefault('parameters', {})

        # Add baseURL option that reads from env
        options = params.setdefault('options', {})
        if 'baseURL' not in options:
            options['baseURL'] = '={{ $env.LLM_BASE_URL }}'
            modified = True

        # Make model name configurable via env with current value as default
        current_model = params.get('model', 'gpt-4o')
        params['model'] = f'={{ $env.LLM_MODEL || "{current_model}" }}'
        modified = True

    if modified:
        with open(filepath, 'w') as f:
            json.dump(wf, f, indent=2)
        print(f"  Patched: {os.path.basename(filepath)}")
        return True
    return False


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    patched = 0
    skipped = 0

    for subdir in WORKFLOW_DIRS:
        search_path = os.path.join(script_dir, subdir, '*.json')
        for filepath in glob.glob(search_path):
            if patch_file(filepath):
                patched += 1
            else:
                skipped += 1

    print(f"\nDone: {patched} patched, {skipped} skipped")


if __name__ == '__main__':
    main()
