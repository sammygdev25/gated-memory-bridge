"""
Session 55a — Scored Extraction Runs
Runs each session (A, B, C, D, E1, E2) through the summarizer 3 times.
Saves raw JSON for every run. Scores against ground truth.
Records everything for the paper.
"""
import os, sys, json, time, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
sys.path.insert(0, os.path.expanduser("~/shikshya-v1.0/backend"))
django.setup()

import anthropic
from api.models.conversation import ChatSession
from api.tasks.chat_memory import _summarize_session_core

with open(os.path.expanduser(
    "~/shikshya-v1.0/backend/eval_scripts/session_ids.json"
)) as f:
    ids = json.load(f)

client = anthropic.Anthropic()

# Ground truth (amended after pilot)
GROUND_TRUTH = {
    "A": {
        "expected_min": 2, "expected_max": 3,
        "decisions": [
            "design_reference: blue header + menu grid + ReservationForm",
            "tech_decision: JWT auth",
        ],
        "noise_items": ["quantum physics", "sunset image", "dinner suggestion"],
    },
    "B": {
        "expected_min": 3, "expected_max": 4,
        "decisions": [
            "project_convention: /api/v1/ prefix",
            "dependency_preference: Stripe",
            "design_reference: ProductCard",
            "tech_decision (borderline): localStorage cart",
        ],
        "noise_items": ["hiking trails", "Tokyo weather"],
    },
    "C": {
        "expected_min": 0, "expected_max": 1,
        "decisions": [
            "dependency_preference (ambiguous): Firebase",
        ],
        "noise_items": ["relativity", "cat image", "philosophy", "jokes", "guitar"],
    },
    "D": {
        "expected_min": 0, "expected_max": 1,
        "decisions": [],
        "noise_items": ["REST vs GraphQL", "PostgreSQL vs SQLite", "microservices", "CAP theorem"],
    },
    "E1": {
        "expected_min": 1, "expected_max": 2,
        "decisions": [
            "tech_decision: session-based auth",
            "design_reference (borderline): login page",
        ],
        "noise_items": [],
    },
    "E2": {
        "expected_min": 1, "expected_max": 2,
        "decisions": [
            "tech_decision: JWT (supersedes session-based)",
            "tech_decision (borderline): refresh tokens",
        ],
        "noise_items": [],
    },
}

all_results = {}
total_cost = 0.0

for session_key in ["A", "B", "C", "D", "E1", "E2"]:
    session = ChatSession.objects.get(id=ids[session_key])
    gt = GROUND_TRUTH[session_key]
    runs = []

    print(f"\n{'='*60}")
    print(f"SESSION {session_key}: {session.title}")
    print(f"Ground truth: {gt['expected_min']}-{gt['expected_max']} proposals")
    print(f"{'='*60}")

    for run_num in range(1, 4):
        print(f"\n  --- Run {run_num}/3 ---")
        start = time.time()
        data, msg_count = _summarize_session_core(session, client)
        elapsed = time.time() - start

        # Estimate cost (Haiku: $0.80/MTok in, $4/MTok out)
        est_input_tokens = msg_count * 150  # rough estimate
        est_output_tokens = 500
        run_cost = (est_input_tokens * 0.80 + est_output_tokens * 4.0) / 1_000_000
        total_cost += run_cost

        if data is None:
            print(f"  ERROR: Summarization returned None")
            runs.append({"run": run_num, "error": "None returned", "cost": run_cost})
            continue

        proposals = data.get("generation_proposals", [])
        print(f"  Proposals extracted: {len(proposals)}")
        print(f"  Time: {elapsed:.1f}s, Est cost: ${run_cost:.4f}")

        for j, p in enumerate(proposals):
            ptype = p.get("type", "?")
            pconf = p.get("confidence", "?")
            pdesc = p.get("description", "")[:60]
            pquote = p.get("source_quote", "")[:50]
            print(f"    [{j}] {ptype}/{pconf}: {pdesc}")
            print(f"        quote: \"{pquote}...\"")

        # Check for noise leakage
        noise_found = []
        for p in proposals:
            desc_lower = json.dumps(p).lower()
            for noise in gt["noise_items"]:
                if noise.lower().split()[0] in desc_lower:
                    noise_found.append(noise)

        if noise_found:
            print(f"  ⚠️ NOISE LEAKED: {noise_found}")
        else:
            print(f"  ✅ No noise leakage")

        run_data = {
            "run": run_num,
            "msg_count": msg_count,
            "elapsed_s": round(elapsed, 2),
            "cost_est": round(run_cost, 6),
            "proposal_count": len(proposals),
            "proposals": proposals,
            "noise_leaked": noise_found,
            "summary_4fields": {
                "project_summary": data["summary"],
                "user_facts": data["user_facts"],
                "key_facts": data["key_facts"],
                "pending_items": data["pending_items"],
            },
        }
        runs.append(run_data)

        # Brief pause between runs to avoid rate limits
        time.sleep(1)

    all_results[session_key] = {
        "ground_truth": gt,
        "runs": runs,
    }

# Save all results
out_path = os.path.expanduser(
    "~/shikshya-v1.0/backend/eval_scripts/scored_runs_raw.json"
)
with open(out_path, "w") as f:
    json.dump(all_results, f, indent=2)

print(f"\n{'='*60}")
print(f"ALL RUNS COMPLETE")
print(f"{'='*60}")
print(f"Total estimated cost: ${total_cost:.4f}")
print(f"Results saved to: {out_path}")

# Quick aggregate stats
print(f"\nQuick summary:")
for sk in ["A", "B", "C", "D", "E1", "E2"]:
    runs = all_results[sk]["runs"]
    gt = all_results[sk]["ground_truth"]
    counts = [r.get("proposal_count", 0) for r in runs if "error" not in r]
    noise_runs = sum(1 for r in runs if r.get("noise_leaked"))
    avg = sum(counts) / len(counts) if counts else 0
    print(f"  {sk}: avg {avg:.1f} proposals (expected {gt['expected_min']}-{gt['expected_max']}), noise in {noise_runs}/3 runs")
