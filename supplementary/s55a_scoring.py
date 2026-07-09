"""
Session 55a — Comprehensive Scoring Pass
Reads scored_runs_raw.json, validates provenance, scores all metrics.
Outputs a scoring table for the paper.
"""
import os, sys, json, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
sys.path.insert(0, os.path.expanduser("~/shikshya-v1.0/backend"))
django.setup()

from api.services.chat.proposal_schema import (
    validate_source_quote, validate_proposal_data, enforce_confidence_tier
)

with open(os.path.expanduser(
    "~/shikshya-v1.0/backend/eval_scripts/scored_runs_raw.json"
)) as f:
    results = json.load(f)

with open(os.path.expanduser(
    "~/shikshya-v1.0/backend/eval_scripts/session_ids.json"
)) as f:
    ids = json.load(f)

# ── Ground truth with per-item detail and acceptable type alternatives ──
GROUND_TRUTH_ITEMS = {
    "A": [
        {"id": "A1", "desc": "blue header + menu grid",
         "primary_type": "design_reference", "alt_types": [],
         "expected_confidence": "confirm"},
        {"id": "A2", "desc": "JWT auth",
         "primary_type": "tech_decision", "alt_types": [],
         "expected_confidence": "confirm"},
        {"id": "A3", "desc": "ReservationForm",
         "primary_type": "design_reference", "alt_types": [],
         "expected_confidence": "confirm", "optional": True},
    ],
    "B": [
        {"id": "B1", "desc": "/api/v1/ prefix",
         "primary_type": "project_convention", "alt_types": ["tech_decision"],
         "expected_confidence": "auto"},
        {"id": "B2", "desc": "Stripe payments",
         "primary_type": "dependency_preference", "alt_types": [],
         "expected_confidence": "auto"},
        {"id": "B3", "desc": "ProductCard component",
         "primary_type": "design_reference", "alt_types": [],
         "expected_confidence": "confirm"},
        {"id": "B4", "desc": "localStorage cart",
         "primary_type": "tech_decision", "alt_types": ["project_convention"],
         "expected_confidence": "confirm", "optional": True},
    ],
    "C": [],  # Zero expected
    "D": [],  # Zero expected
    "E1": [
        {"id": "E1a", "desc": "session-based auth",
         "primary_type": "tech_decision", "alt_types": [],
         "expected_confidence": "confirm"},
        {"id": "E1b", "desc": "login page design",
         "primary_type": "design_reference", "alt_types": [],
         "expected_confidence": "confirm", "optional": True},
    ],
    "E2": [
        {"id": "E2a", "desc": "JWT switch",
         "primary_type": "tech_decision", "alt_types": [],
         "expected_confidence": "confirm"},
        {"id": "E2b", "desc": "refresh tokens",
         "primary_type": "tech_decision", "alt_types": [],
         "expected_confidence": "confirm", "optional": True},
    ],
}

# Keywords for matching proposals to ground truth items
MATCH_KEYWORDS = {
    "A1": ["header", "menu", "grid"],
    "A2": ["jwt", "authentication", "auth"],
    "A3": ["reservation"],
    "B1": ["api/v1", "prefix", "versioning"],
    "B2": ["stripe", "payment"],
    "B3": ["product", "card", "productcard"],
    "B4": ["localstorage", "cart", "persist"],
    "E1a": ["session", "cookie"],
    "E1b": ["login", "email", "password"],
    "E2a": ["jwt", "switch"],
    "E2b": ["refresh", "token", "15"],
}

def match_proposal_to_gt(proposal, gt_items):
    """Match a proposal to a ground truth item using keywords."""
    prop_text = json.dumps(proposal).lower()
    best_match = None
    best_score = 0
    for item in gt_items:
        keywords = MATCH_KEYWORDS.get(item["id"], [])
        score = sum(1 for kw in keywords if kw in prop_text)
        if score > best_score:
            best_score = score
            best_match = item
    return best_match if best_score > 0 else None

# ── Scoring ──
all_scores = {}
agg = {
    "total_proposals": 0,
    "correct_proposals": 0,
    "noise_proposals": 0,
    "type_correct_strict": 0,
    "type_correct_lenient": 0,
    "type_total": 0,
    "conf_raw_correct": 0,
    "conf_enforced_correct": 0,
    "conf_total": 0,
    "provenance_pass": 0,
    "provenance_fail": 0,
    "provenance_total": 0,
    "recall_hits": {},  # item_id -> count of runs it was found
    "recall_possible": {},  # item_id -> total runs
}

for session_key in ["A", "B", "C", "D", "E1", "E2"]:
    gt_items = GROUND_TRUTH_ITEMS[session_key]
    session_id = ids[session_key]
    runs = results[session_key]["runs"]
    session_scores = []

    # Init recall tracking
    for item in gt_items:
        if item["id"] not in agg["recall_hits"]:
            agg["recall_hits"][item["id"]] = 0
            agg["recall_possible"][item["id"]] = 0

    for run_data in runs:
        if "error" in run_data:
            continue

        proposals = run_data.get("proposals", [])
        run_score = {
            "run": run_data["run"],
            "proposal_count": len(proposals),
            "matched": [],
            "unmatched": [],
            "noise": [],
            "type_strict": 0,
            "type_lenient": 0,
            "conf_raw_correct": 0,
            "conf_enforced_correct": 0,
            "provenance_pass": 0,
            "provenance_fail": 0,
        }

        matched_gt_ids = set()

        for prop in proposals:
            agg["total_proposals"] += 1
            gt_match = match_proposal_to_gt(prop, gt_items)

            if gt_match and gt_match["id"] not in matched_gt_ids:
                matched_gt_ids.add(gt_match["id"])
                agg["correct_proposals"] += 1
                run_score["matched"].append({
                    "gt_id": gt_match["id"],
                    "gt_desc": gt_match["desc"],
                    "extracted_type": prop.get("type"),
                    "expected_type": gt_match["primary_type"],
                })

                # Type accuracy
                agg["type_total"] += 1
                if prop.get("type") == gt_match["primary_type"]:
                    agg["type_correct_strict"] += 1
                    agg["type_correct_lenient"] += 1
                    run_score["type_strict"] += 1
                    run_score["type_lenient"] += 1
                elif prop.get("type") in gt_match.get("alt_types", []):
                    agg["type_correct_lenient"] += 1
                    run_score["type_lenient"] += 1

                # Confidence accuracy (raw)
                agg["conf_total"] += 1
                raw_conf = prop.get("confidence", "confirm")
                expected_conf = gt_match["expected_confidence"]
                if raw_conf == expected_conf:
                    agg["conf_raw_correct"] += 1
                    run_score["conf_raw_correct"] += 1

                # Confidence accuracy (post-enforcement)
                enforced_conf = enforce_confidence_tier(
                    prop.get("type", ""), raw_conf
                )
                if enforced_conf == expected_conf:
                    agg["conf_enforced_correct"] += 1
                    run_score["conf_enforced_correct"] += 1

            elif gt_match and gt_match["id"] in matched_gt_ids:
                # Duplicate match — count as extra, not noise
                run_score["unmatched"].append(prop.get("description", "")[:40])
            else:
                agg["noise_proposals"] += 1
                run_score["noise"].append(prop.get("description", "")[:40])

            # Provenance validation
            quote = prop.get("source_quote", "")
            agg["provenance_total"] += 1
            if validate_source_quote(session_id, quote):
                agg["provenance_pass"] += 1
                run_score["provenance_pass"] += 1
            else:
                agg["provenance_fail"] += 1
                run_score["provenance_fail"] += 1

        # Recall: which GT items were found this run
        for item in gt_items:
            agg["recall_possible"][item["id"]] = agg["recall_possible"].get(
                item["id"], 0
            ) + 1
            if item["id"] in matched_gt_ids:
                agg["recall_hits"][item["id"]] = agg["recall_hits"].get(
                    item["id"], 0
                ) + 1

        session_scores.append(run_score)

    all_scores[session_key] = session_scores

# ── Print Results ──
print("=" * 70)
print("SESSION 55a — COMPREHENSIVE SCORING RESULTS")
print("=" * 70)

# Per-session detail
for sk in ["A", "B", "C", "D", "E1", "E2"]:
    print(f"\n--- Session {sk} ---")
    for rs in all_scores[sk]:
        matched_ids = [m["gt_id"] for m in rs["matched"]]
        print(f"  Run {rs['run']}: {rs['proposal_count']} proposals, "
              f"matched={matched_ids}, noise={len(rs['noise'])}, "
              f"provenance={rs['provenance_pass']}/{rs['provenance_pass']+rs['provenance_fail']}")

# Aggregate metrics
total = agg["total_proposals"]
correct = agg["correct_proposals"]
noise = agg["noise_proposals"]

precision = correct / total if total else 0
# Recall: count required GT items found at least once / total required GT items
required_items = [
    item for items in GROUND_TRUTH_ITEMS.values()
    for item in items if not item.get("optional")
]
required_found = sum(
    1 for item in required_items
    if agg["recall_hits"].get(item["id"], 0) > 0
)
recall = required_found / len(required_items) if required_items else 0

type_strict = agg["type_correct_strict"] / agg["type_total"] if agg["type_total"] else 0
type_lenient = agg["type_correct_lenient"] / agg["type_total"] if agg["type_total"] else 0
conf_raw = agg["conf_raw_correct"] / agg["conf_total"] if agg["conf_total"] else 0
conf_enforced = agg["conf_enforced_correct"] / agg["conf_total"] if agg["conf_total"] else 0
prov_rate = agg["provenance_pass"] / agg["provenance_total"] if agg["provenance_total"] else 0

print(f"\n{'='*70}")
print(f"AGGREGATE METRICS")
print(f"{'='*70}")
print(f"Total proposals extracted:     {total}")
print(f"Correctly matched:             {correct}")
print(f"Noise/false positives:         {noise}")
print(f"")
print(f"Extraction Precision:          {precision:.1%} ({correct}/{total})")
print(f"Extraction Recall (required):  {recall:.1%} ({required_found}/{len(required_items)})")
print(f"")
print(f"Type Accuracy (strict):        {type_strict:.1%}")
print(f"Type Accuracy (lenient):       {type_lenient:.1%}")
print(f"")
print(f"Confidence Accuracy (raw LLM): {conf_raw:.1%}")
print(f"Confidence Accuracy (enforced):{conf_enforced:.1%}")
print(f"  → Delta (gate value):        {conf_enforced - conf_raw:+.1%}")
print(f"")
print(f"Provenance Validation Rate:    {prov_rate:.1%} ({agg['provenance_pass']}/{agg['provenance_total']})")

# Per-item recall
print(f"\n--- Per-Item Recall (across 3 runs each) ---")
for sk in ["A", "B", "C", "D", "E1", "E2"]:
    for item in GROUND_TRUTH_ITEMS[sk]:
        hits = agg["recall_hits"].get(item["id"], 0)
        possible = agg["recall_possible"].get(item["id"], 0)
        opt = " (optional)" if item.get("optional") else ""
        print(f"  {item['id']}: {hits}/{possible} — {item['desc']}{opt}")

# Criteria check
print(f"\n{'='*70}")
print(f"CRITERIA CHECK")
print(f"{'='*70}")
checks = [
    (f"Precision >= 80%: {precision:.1%}", precision >= 0.80),
    (f"Recall >= 70%: {recall:.1%}", recall >= 0.70),
    (f"Provenance >= 90%: {prov_rate:.1%}", prov_rate >= 0.90),
    (f"Session D <= 1 proposal per run: max={max(r['proposal_count'] for r in all_scores['D'])}", max(r['proposal_count'] for r in all_scores['D']) <= 1),
]
for desc, passed in checks:
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status}: {desc}")

# Save
out_path = os.path.expanduser(
    "~/shikshya-v1.0/backend/eval_scripts/scoring_results.json"
)
with open(out_path, "w") as f:
    json.dump({
        "per_session": all_scores,
        "aggregate": {
            "total_proposals": total,
            "correct": correct,
            "noise": noise,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "type_strict": round(type_strict, 4),
            "type_lenient": round(type_lenient, 4),
            "conf_raw": round(conf_raw, 4),
            "conf_enforced": round(conf_enforced, 4),
            "provenance_rate": round(prov_rate, 4),
        },
        "per_item_recall": {
            item["id"]: {
                "hits": agg["recall_hits"].get(item["id"], 0),
                "possible": agg["recall_possible"].get(item["id"], 0),
                "desc": item["desc"],
            }
            for items in GROUND_TRUTH_ITEMS.values()
            for item in items
        },
    }, f, indent=2)
print(f"\nScoring results saved to: {out_path}")
