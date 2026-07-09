"""
Session 55a — Cleanup
Removes test user, test sessions, proposals, summaries, and semantic memory.
Run AFTER all scoring is complete and results are saved.
"""
import os, sys, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
sys.path.insert(0, os.path.expanduser("~/shikshya-v1.0/backend"))
django.setup()

from django.contrib.auth.models import User
from api.models.conversation import ChatSession, ChatMessage
from api.models.chat_summary import ChatSessionSummary
from api.models.generation_proposal import GenerationProposal
from api.models.agent_memory import SemanticMemory, EpisodicMemory

try:
    user = User.objects.get(username="shikshya_eval_user")
    user_id = user.id

    p_count = GenerationProposal.objects.filter(user=user).delete()[0]
    print(f"Deleted {p_count} proposals")

    s_count = ChatSessionSummary.objects.filter(user=user).delete()[0]
    print(f"Deleted {s_count} summaries")

    sm_count = SemanticMemory.objects.filter(user=user).delete()[0]
    print(f"Deleted {sm_count} semantic memories")

    em_count = EpisodicMemory.objects.filter(user=user).delete()[0]
    print(f"Deleted {em_count} episodic memories")

    msg_count = ChatMessage.objects.filter(session__user=user).delete()[0]
    print(f"Deleted {msg_count} messages")

    sess_count = ChatSession.objects.filter(user=user).delete()[0]
    print(f"Deleted {sess_count} sessions")

    user.delete()
    print(f"Deleted test user (id={user_id})")

    print("\n✅ Cleanup complete — all eval data removed")

except User.DoesNotExist:
    print("Test user not found — already cleaned up")
except Exception as e:
    print(f"Cleanup error: {e}")
