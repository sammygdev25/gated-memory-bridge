"""
Session 55a — Multi-Session Contamination Test
The real poisoning scenario: accumulated history from multiple projects.

Naive: Concatenate A (restaurant) + B (e-commerce) + E1 + E2 (auth flip)
       as accumulated conversation history. Ask: "build the restaurant app."
       Expected: Stripe/ProductCard bleed, possibly session-auth despite JWT switch.

Gated: Inject only restaurant project's approved proposals.
       Expected: Clean restaurant-only output.

Also reports token counts for both contexts.
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
    "list ALL the Django models and React components you would create "
    "for THE RESTAURANT APP (TastyBites). "
    "Return a JSON object with two arrays:\n"
    '  "models": ["ModelName1", ...]\n'
    '  "components": ["ComponentName1", ...]\n'
    "Include EVERY model and component the context suggests for TastyBites. "
    "Return ONLY valid JSON, no explanation."
)

# ── Build naive context: all 4 sessions concatenated ──
print("Building multi-session naive context...")
naive_context = "CONVERSATION HISTORY (accumulated across sessions):\n\n"
total_naive_chars = 0

for sk in ["A", "B", "E1", "E2"]:
    session = ChatSession.objects.get(id=ids[sk])
    messages = list(
        ChatMessage.objects.filter(session=session)
        .order_by("created_at")
        .values("role", "content")
    )
    naive_context += f"--- Session: {session.title} ---\n"
    for m in messages:
        naive_context += f"{m['role']}: {m['content']}\n"
    naive_context += "\n"

naive_context += "Based on ALL the above conversations, plan the TastyBites restaurant app."
total_naive_chars = len(naive_context)
naive_tokens_est = total_naive_chars // 4  # rough char-to-token

print(f"Naive context: {total_naive_chars} chars (~{naive_tokens_est} tokens)")

# ── Build gated context: only restaurant proposals from run 1 ──
print("Building gated context...")
proposals_a = scored["A"]["runs"][0].get("proposals", [])

gated_context = "APPROVED PROJECT DECISIONS (TastyBites restaurant app):\n"
for p in proposals_a:
    ptype = p.get("type", "")
    pdata = p.get("data", {})
    if ptype == "design_reference":
        comps = pdata.get("components", [])
        colors = pdata.get("color_scheme", {})
        desc = pdata.get("description", "")
        gated_context += f"- Design: {', '.join(comps)}"
        if colors:
            gated_context += f" (colors: {colors})"
        if desc:
            gated_context += f" — {desc}"
        gated_context += "\n"
    elif ptype == "tech_decision":
        gated_context += f"- Tech: {pdata.get('decision', '')} (topic: {pdata.get('topic', '')})\n"
    elif ptype == "project_convention":
        gated_context += f"- Convention: {pdata.get('pattern', '')} (scope: {pdata.get('scope', '')})\n"
    elif ptype == "dependency_preference":
        gated_context += f"- Dependency: {pdata.get('package', '')} — {pdata.get('reason', '')}\n"

gated_context += "\nBased on these approved decisions, plan the TastyBites restaurant app."
total_gated_chars = len(gated_context)
gated_tokens_est = total_gated_chars // 4

print(f"Gated context: {total_gated_chars} chars (~{gated_tokens_est} tokens)")
print(f"Token ratio: {naive_tokens_est / max(gated_tokens_est, 1):.1f}x")

# ── E-commerce bleed keywords (should NOT appear in restaurant app) ──
ECOMMERCE_BLEED = [
    "stripe", "payment", "checkout", "cart", "ecommerce", "shopwave",
    "productcard", "product_card", "shopping", "order", "orderitem",
]
AUTH_BLEED = [
    "session_auth", "session-based", "httponly", "cookie",
    # Note: "session" alone is too broad — Django uses sessions legitimately
]

# ── Run naive ──
print(f"\n{'='*60}")
print("NAIVE — Multi-session dump")
print(f"{'='*60}")

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
    naive_data = {"models": [], "components": [], "parse_error": naive_raw[:300]}

naive_models = naive_data.get("models", [])
naive_components = naive_data.get("components", [])
naive_all_lower = [x.lower().replace(" ", "") for x in naive_models + naive_components]

ecom_bleed = [item for item in naive_all_lower
              if any(kw in item for kw in ECOMMERCE_BLEED)]
auth_bleed = [item for item in naive_all_lower
              if any(kw in item for kw in AUTH_BLEED)]

print(f"Models: {naive_models}")
print(f"Components: {naive_components}")
print(f"Total: {len(naive_models) + len(naive_components)}")
print(f"E-commerce bleed: {ecom_bleed if ecom_bleed else 'NONE'}")
print(f"Stale auth bleed: {auth_bleed if auth_bleed else 'NONE'}")

# ── Run gated ──
print(f"\n{'='*60}")
print("GATED — Approved proposals only")
print(f"{'='*60}")

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
    gated_data = {"models": [], "components": [], "parse_error": gated_raw[:300]}

gated_models = gated_data.get("models", [])
gated_components = gated_data.get("components", [])
gated_all_lower = [x.lower().replace(" ", "") for x in gated_models + gated_components]

ecom_bleed_gated = [item for item in gated_all_lower
                    if any(kw in item for kw in ECOMMERCE_BLEED)]
auth_bleed_gated = [item for item in gated_all_lower
                    if any(kw in item for kw in AUTH_BLEED)]

print(f"Models: {gated_models}")
print(f"Components: {gated_components}")
print(f"Total: {len(gated_models) + len(gated_components)}")
print(f"E-commerce bleed: {ecom_bleed_gated if ecom_bleed_gated else 'NONE'}")
print(f"Stale auth bleed: {auth_bleed_gated if auth_bleed_gated else 'NONE'}")

# ── Summary ──
print(f"\n{'='*60}")
print("MULTI-SESSION CONTAMINATION SUMMARY")
print(f"{'='*60}")
print(f"Token economy:")
print(f"  Naive context:  ~{naive_tokens_est} tokens")
print(f"  Gated context:  ~{gated_tokens_est} tokens")
print(f"  Ratio:          {naive_tokens_est / max(gated_tokens_est, 1):.1f}x reduction")
print(f"")
print(f"Cross-project contamination:")
print(f"  Naive e-commerce bleed:    {len(ecom_bleed)} items {ecom_bleed}")
print(f"  Gated e-commerce bleed:    {len(ecom_bleed_gated)} items {ecom_bleed_gated}")
print(f"  Naive stale-auth bleed:    {len(auth_bleed)} items {auth_bleed}")
print(f"  Gated stale-auth bleed:    {len(auth_bleed_gated)} items {auth_bleed_gated}")

total_naive_bleed = len(ecom_bleed) + len(auth_bleed)
total_gated_bleed = len(ecom_bleed_gated) + len(auth_bleed_gated)
print(f"")
print(f"Total contamination:")
print(f"  Naive: {total_naive_bleed} items")
print(f"  Gated: {total_gated_bleed} items")

# Save
results = {
    "token_economy": {
        "naive_chars": total_naive_chars,
        "naive_tokens_est": naive_tokens_est,
        "gated_chars": total_gated_chars,
        "gated_tokens_est": gated_tokens_est,
        "ratio": round(naive_tokens_est / max(gated_tokens_est, 1), 1),
    },
    "naive": {
        "models": naive_models,
        "components": naive_components,
        "ecommerce_bleed": ecom_bleed,
        "auth_bleed": auth_bleed,
    },
    "gated": {
        "models": gated_models,
        "components": gated_components,
        "ecommerce_bleed": ecom_bleed_gated,
        "auth_bleed": auth_bleed_gated,
    },
}
out_path = os.path.expanduser(
    "~/shikshya-v1.0/backend/eval_scripts/multisession_results.json"
)
with open(out_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"\nResults saved to: {out_path}")
