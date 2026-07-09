"""
Step 11: 4-field regression check.
Runs the summarizer on Session A once and prints all 5 fields.
Verify existing 4 fields are high quality before running full eval.
"""
import os, sys, json, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
sys.path.insert(0, os.path.expanduser("~/shikshya-v1.0/backend"))
django.setup()

import anthropic
from api.models.conversation import ChatSession
from api.tasks.chat_memory import _summarize_session_core

# Load session IDs
with open(os.path.expanduser(
    "~/shikshya-v1.0/backend/eval_scripts/session_ids.json"
)) as f:
    ids = json.load(f)

session = ChatSession.objects.get(id=ids["A"])
client = anthropic.Anthropic()

print("=" * 60)
print("REGRESSION CHECK — Session A (Restaurant App)")
print("=" * 60)

data, msg_count = _summarize_session_core(session, client)

if data is None:
    print("ERROR: Summarization returned None")
    sys.exit(1)

print(f"\nMessages processed: {msg_count}")
print(f"\n--- 1. project_summary ---")
print(data["summary"])
print(f"\n--- 2. user_facts ---")
print(json.dumps(data["user_facts"], indent=2))
print(f"\n--- 3. key_facts ---")
print(json.dumps(data["key_facts"], indent=2))
print(f"\n--- 4. pending_items ---")
print(json.dumps(data["pending_items"], indent=2))
print(f"\n--- 5. generation_proposals (NEW) ---")
print(json.dumps(data.get("generation_proposals", []), indent=2))

# Quick quality check
checks = []
summary = data["summary"]
if summary and len(summary) > 20:
    checks.append("✅ project_summary is substantive")
else:
    checks.append("❌ project_summary is empty or too short")

if isinstance(data["user_facts"], list):
    checks.append(f"✅ user_facts is a list ({len(data['user_facts'])} items)")
else:
    checks.append("❌ user_facts is not a list")

if isinstance(data["key_facts"], list):
    checks.append(f"✅ key_facts is a list ({len(data['key_facts'])} items)")
else:
    checks.append("❌ key_facts is not a list")

if isinstance(data["pending_items"], list):
    checks.append(f"✅ pending_items is a list ({len(data['pending_items'])} items)")
else:
    checks.append("❌ pending_items is not a list")

proposals = data.get("generation_proposals", [])
if isinstance(proposals, list):
    checks.append(f"✅ generation_proposals is a list ({len(proposals)} items)")
else:
    checks.append("❌ generation_proposals is not a list")

print(f"\n--- Quality Checks ---")
for c in checks:
    print(c)

# Estimate cost
# Haiku input: ~66 msgs * ~250 chars avg = ~16K chars = ~4K tokens
# Haiku output: ~800 tokens max
# Haiku pricing: $0.80/MTok input, $4/MTok output
est_cost = (4000 * 0.80 + 800 * 4.0) / 1_000_000
print(f"\nEstimated cost: ~${est_cost:.4f}")
