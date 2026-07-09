"""
Session 55a — Naive vs Gated Bridging Comparison
For each test session (A, B, C, D):
  - Naive: dump full conversation into a generation prompt, ask what to build
  - Gated: inject only approved proposals, ask the same question
Count irrelevant artifacts in each approach.
"""
import os, sys, json, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
sys.path.insert(0, os.path.expanduser("~/shikshya-v1.0/backend"))
django.setup()

import anthropic
from api.models.conversation import ChatSession, ChatMessage

with open(os.path.expanduser(
    "~/shikshya-v1.0/backend/eval_scripts/session_ids.json"
)) as f:
    ids = json.load(f)

with open(os.path.expanduser(
    "~/shikshya-v1.0/backend/eval_scripts/scored_runs_raw.json"
)) as f:
    scored = json.load(f)

client = anthropic.Anthropic()

GENERATION_PROMPT = (
    "You are a code generation planner. Based on the context provided, "
    "list ALL the Django models and React components you would create. "
    "Return a JSON object with two arrays:\n"
    '  "models": ["ModelName1", "ModelName2", ...]\n'
    '  "components": ["ComponentName1", "ComponentName2", ...]\n'
    "Include EVERY model and component the context suggests. "
    "Return ONLY valid JSON, no explanation."
)

# Noise keywords — if these appear in model/component names, it's poisoning
NOISE_KEYWORDS = [
    "quantum", "entangle", "photon", "sunset", "dinner", "italian",
    "thai", "hiking", "trail", "weather", "tokyo", "relativity",
    "einstein", "cat", "tophat", "philosophy", "joke", "guitar",
    "rest", "graphql", "cap", "theorem", "kubernetes", "microservice",
    "scaling", "firebase",
]

results = {}
total_cost = 0.0

for session_key in ["A", "B", "C", "D"]:
    session = ChatSession.objects.get(id=ids[session_key])
    messages = list(
        ChatMessage.objects.filter(session=session)
        .order_by("created_at")
        .values("role", "content")
    )

    print(f"\n{'='*60}")
    print(f"SESSION {session_key}: {session.title}")
    print(f"{'='*60}")

    # ── Naive bridging: dump full conversation ──
    naive_context = "CONVERSATION HISTORY:\n"
    for m in messages:
        naive_context += f"{m['role']}: {m['content']}\n"
    naive_context += "\nBased on this conversation, plan the application."

    print("\n  --- NAIVE (full conversation dump) ---")
    response_naive = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=GENERATION_PROMPT,
        messages=[{"role": "user", "content": naive_context}],
    )
    naive_raw = response_naive.content[0].text.strip()
    if naive_raw.startswith("```"):
        naive_raw = naive_raw.split("\n", 1)[-1]
    if naive_raw.endswith("```"):
        naive_raw = naive_raw.rsplit("```", 1)[0]

    try:
        naive_data = json.loads(naive_raw.strip())
    except json.JSONDecodeError:
        naive_data = {"models": [], "components": [], "parse_error": naive_raw[:200]}

    naive_models = naive_data.get("models", [])
    naive_components = naive_data.get("components", [])
    naive_all = [x.lower() for x in naive_models + naive_components]

    naive_noise = []
    for item in naive_all:
        for kw in NOISE_KEYWORDS:
            if kw in item:
                naive_noise.append(item)
                break

    total_naive = len(naive_models) + len(naive_components)
    print(f"  Models: {naive_models}")
    print(f"  Components: {naive_components}")
    print(f"  Total items: {total_naive}")
    print(f"  Noise items: {naive_noise} ({len(naive_noise)})")

    # ── Gated bridging: only approved proposals ──
    # Use run 1's proposals as the approved set
    run1 = scored[session_key]["runs"][0]
    proposals = run1.get("proposals", [])

    if proposals:
        gated_context = "APPROVED PROJECT DECISIONS:\n"
        for p in proposals:
            ptype = p.get("type", "")
            pdata = p.get("data", {})
            if ptype == "design_reference":
                comps = pdata.get("components", [])
                colors = pdata.get("color_scheme", {})
                gated_context += f"- Components: {', '.join(comps)}\n"
                if colors:
                    gated_context += f"- Color scheme: {colors}\n"
            elif ptype == "tech_decision":
                gated_context += f"- Tech: {pdata.get('decision', '')}\n"
            elif ptype == "project_convention":
                gated_context += f"- Convention: {pdata.get('pattern', '')} (scope: {pdata.get('scope', '')})\n"
            elif ptype == "dependency_preference":
                gated_context += f"- Dependency: {pdata.get('package', '')} — {pdata.get('reason', '')}\n"
        gated_context += "\nBased on these approved decisions, plan the application."
    else:
        gated_context = "No project decisions have been made. Plan a minimal application."

    print("\n  --- GATED (approved proposals only) ---")
    response_gated = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=GENERATION_PROMPT,
        messages=[{"role": "user", "content": gated_context}],
    )
    gated_raw = response_gated.content[0].text.strip()
    if gated_raw.startswith("```"):
        gated_raw = gated_raw.split("\n", 1)[-1]
    if gated_raw.endswith("```"):
        gated_raw = gated_raw.rsplit("```", 1)[0]

    try:
        gated_data = json.loads(gated_raw.strip())
    except json.JSONDecodeError:
        gated_data = {"models": [], "components": [], "parse_error": gated_raw[:200]}

    gated_models = gated_data.get("models", [])
    gated_components = gated_data.get("components", [])
    gated_all = [x.lower() for x in gated_models + gated_components]

    gated_noise = []
    for item in gated_all:
        for kw in NOISE_KEYWORDS:
            if kw in item:
                gated_noise.append(item)
                break

    total_gated = len(gated_models) + len(gated_components)
    print(f"  Models: {gated_models}")
    print(f"  Components: {gated_components}")
    print(f"  Total items: {total_gated}")
    print(f"  Noise items: {gated_noise} ({len(gated_noise)})")

    # Cost estimate (Sonnet: $3/MTok in, $15/MTok out)
    run_cost = 2 * (2000 * 3.0 + 500 * 15.0) / 1_000_000
    total_cost += run_cost

    results[session_key] = {
        "naive": {
            "models": naive_models,
            "components": naive_components,
            "total": total_naive,
            "noise": naive_noise,
            "noise_count": len(naive_noise),
        },
        "gated": {
            "models": gated_models,
            "components": gated_components,
            "total": total_gated,
            "noise": gated_noise,
            "noise_count": len(gated_noise),
        },
    }

# ── Summary ──
print(f"\n{'='*60}")
print(f"NAIVE vs GATED — SUMMARY")
print(f"{'='*60}")

total_naive_items = sum(r["naive"]["total"] for r in results.values())
total_naive_noise = sum(r["naive"]["noise_count"] for r in results.values())
total_gated_items = sum(r["gated"]["total"] for r in results.values())
total_gated_noise = sum(r["gated"]["noise_count"] for r in results.values())

naive_rate = total_naive_noise / total_naive_items if total_naive_items else 0
gated_rate = total_gated_noise / total_gated_items if total_gated_items else 0

for sk in ["A", "B", "C", "D"]:
    r = results[sk]
    print(f"  {sk}: naive={r['naive']['noise_count']}/{r['naive']['total']} noise, "
          f"gated={r['gated']['noise_count']}/{r['gated']['total']} noise")

print(f"\nAggregate poisoning rates:")
print(f"  Naive:  {naive_rate:.1%} ({total_naive_noise}/{total_naive_items})")
print(f"  Gated:  {gated_rate:.1%} ({total_gated_noise}/{total_gated_items})")
print(f"  Reduction: {naive_rate - gated_rate:.1%}")
print(f"\nEstimated cost: ${total_cost:.4f}")

# Save
out_path = os.path.expanduser(
    "~/shikshya-v1.0/backend/eval_scripts/naive_vs_gated_results.json"
)
with open(out_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"Results saved to: {out_path}")
