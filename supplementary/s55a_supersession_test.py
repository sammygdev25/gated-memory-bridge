"""
Session 55a — Supersession Test
1. Run E1 through the full save pipeline (proposals saved to DB)
2. Manually approve E1's session-based auth proposal
3. Run E2 through the full save pipeline
4. Verify: E1's auth proposal is superseded, E2's JWT is approved
5. Verify: E2's refresh-token proposal is NOT superseded (same-session exclusion)
"""
import os, sys, json, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
sys.path.insert(0, os.path.expanduser("~/shikshya-v1.0/backend"))
django.setup()

import anthropic
from django.utils import timezone
from api.models.conversation import ChatSession
from api.models.generation_proposal import GenerationProposal
from api.tasks.chat_memory import _summarize_session_core, _save_proposals

with open(os.path.expanduser(
    "~/shikshya-v1.0/backend/eval_scripts/session_ids.json"
)) as f:
    ids = json.load(f)

# Clean any prior test proposals
user_id = ChatSession.objects.get(id=ids["E1"]).user_id
GenerationProposal.objects.filter(user_id=user_id).delete()
print("Cleaned prior proposals")

client = anthropic.Anthropic()

# ── Step 1: Run E1 through summarizer + save ──
print("\n--- Step 1: Extract + save E1 proposals ---")
session_e1 = ChatSession.objects.get(id=ids["E1"])
data_e1, mc_e1 = _summarize_session_core(session_e1, client)

if data_e1 is None:
    print("ERROR: E1 summarization failed")
    sys.exit(1)

saved_e1 = _save_proposals(session_e1, data_e1, "securevault")
print(f"E1: saved {saved_e1} proposals")

# Show what was saved
e1_proposals = list(GenerationProposal.objects.filter(
    user=session_e1.user, source_session_id=ids["E1"]
).values("id", "schema_type", "status", "confidence_tier", "description"))
for p in e1_proposals:
    print(f"  [{p['id']}] {p['schema_type']}/{p['confidence_tier']}/{p['status']}: {p['description'][:50]}")

# ── Step 2: Manually approve E1's tech_decision (simulating S55b confirm flow) ──
print("\n--- Step 2: Approve E1's session-based auth ---")
e1_auth = GenerationProposal.objects.filter(
    user=session_e1.user,
    source_session_id=ids["E1"],
    schema_type="tech_decision",
).first()

if e1_auth:
    e1_auth.status = "approved"
    e1_auth.approved_at = timezone.now()
    e1_auth.save()
    print(f"  Approved: [{e1_auth.id}] {e1_auth.description[:50]}")

    # Now run supersession check (as if this just got approved)
    from api.services.chat.proposal_schema import check_supersession
    superseded = check_supersession(
        session_e1.user, "securevault", "tech_decision",
        e1_auth.proposal_data, source_session_id=ids["E1"],
    )
    print(f"  Superseded by E1 approval: {superseded} (should be 0)")
else:
    print("  WARNING: No tech_decision found in E1")

# ── Step 3: Run E2 through summarizer + save ──
print("\n--- Step 3: Extract + save E2 proposals ---")
session_e2 = ChatSession.objects.get(id=ids["E2"])
data_e2, mc_e2 = _summarize_session_core(session_e2, client)

if data_e2 is None:
    print("ERROR: E2 summarization failed")
    sys.exit(1)

saved_e2 = _save_proposals(session_e2, data_e2, "securevault")
print(f"E2: saved {saved_e2} proposals")

# ── Step 4: Check DB state ──
print("\n--- Step 4: Final DB state ---")
all_proposals = list(GenerationProposal.objects.filter(
    user=session_e1.user, project_name="securevault"
).order_by("created_at").values(
    "id", "schema_type", "status", "confidence_tier",
    "source_session_id", "description"
))

for p in all_proposals:
    session_label = "E1" if p["source_session_id"] == ids["E1"] else "E2"
    print(f"  [{p['id']}] {session_label} {p['schema_type']}/{p['status']}: {p['description'][:50]}")

# ── Step 5: Verify supersession ──
print("\n--- Step 5: Supersession verification ---")

# E1's auth should still be approved (E2 proposals are proposed/auto, not approved yet)
e1_auth_check = GenerationProposal.objects.filter(
    source_session_id=ids["E1"], schema_type="tech_decision"
).first()

# Now simulate approving E2's JWT proposal
e2_jwt = GenerationProposal.objects.filter(
    source_session_id=ids["E2"], schema_type="tech_decision",
    description__icontains="jwt"
).first()

if e2_jwt:
    print(f"\n  Approving E2 JWT: [{e2_jwt.id}]")
    e2_jwt.status = "approved"
    e2_jwt.approved_at = timezone.now()
    e2_jwt.save()

    from api.services.chat.proposal_schema import check_supersession
    superseded = check_supersession(
        session_e2.user, "securevault", "tech_decision",
        e2_jwt.proposal_data, source_session_id=ids["E2"],
    )
    print(f"  Superseded count: {superseded}")

    # Reload E1's auth
    e1_auth_check.refresh_from_db()
    print(f"  E1 auth status now: {e1_auth_check.status} (should be 'superseded')")

# Now approve E2's refresh token proposal
e2_refresh = GenerationProposal.objects.filter(
    source_session_id=ids["E2"], schema_type="tech_decision",
).exclude(id=e2_jwt.id if e2_jwt else -1).first()

if e2_refresh:
    print(f"\n  Approving E2 refresh token: [{e2_refresh.id}]")
    e2_refresh.status = "approved"
    e2_refresh.approved_at = timezone.now()
    e2_refresh.save()

    superseded2 = check_supersession(
        session_e2.user, "securevault", "tech_decision",
        e2_refresh.proposal_data, source_session_id=ids["E2"],
    )
    print(f"  Superseded count: {superseded2}")

    # Reload E2 JWT — should still be approved (same-session exclusion)
    e2_jwt.refresh_from_db()
    print(f"  E2 JWT status now: {e2_jwt.status} (should STILL be 'approved')")

# Final summary
print("\n--- Final State ---")
final = GenerationProposal.objects.filter(
    user=session_e1.user, project_name="securevault"
).order_by("created_at")
for p in final:
    sl = "E1" if p.source_session_id == ids["E1"] else "E2"
    print(f"  {sl} {p.schema_type}/{p.status}: {p.description[:50]}")

approved_auth = final.filter(schema_type="tech_decision", status="approved")
superseded_auth = final.filter(schema_type="tech_decision", status="superseded")
print(f"\nApproved tech_decisions: {approved_auth.count()} (should be 2: JWT + refresh)")
print(f"Superseded tech_decisions: {superseded_auth.count()} (should be 1: session-based)")

success = (
    approved_auth.count() >= 2 and
    superseded_auth.count() >= 1 and
    e2_jwt and e2_jwt.status == "approved"
)
print(f"\n{'✅ SUPERSESSION TEST PASSED' if success else '❌ SUPERSESSION TEST FAILED'}")
