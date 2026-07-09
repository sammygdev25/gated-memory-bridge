"""
Session 55a Evaluation — Setup Script
Creates test user (shikshya_eval_user) and 6 chat sessions
(A, B, C, D, E1, E2) with ground-truth labels for extraction eval.

Session E is split into two sessions for supersession testing.

Usage:
    cd ~/shikshya-v1.0/backend
    DJANGO_SETTINGS_MODULE=core.settings python eval_scripts/s55a_setup.py

Cleanup:
    DJANGO_SETTINGS_MODULE=core.settings python eval_scripts/s55a_cleanup.py
"""
import os, sys, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
sys.path.insert(0, os.path.expanduser("~/shikshya-v1.0/backend"))
django.setup()

from django.contrib.auth.models import User
from api.models.conversation import ChatSession, ChatMessage

# Create or get test user
user, created = User.objects.get_or_create(
    username="shikshya_eval_user",
    defaults={"email": "eval@test.local", "is_active": True},
)
if created:
    user.set_password("CHANGE_ME_EVAL_PASSWORD")
    user.save()
    print(f"Created test user: {user.username} (id={user.id})")
else:
    print(f"Using existing test user: {user.username} (id={user.id})")

# Clean up any prior eval sessions
old_sessions = ChatSession.objects.filter(user=user)
old_count = old_sessions.count()
if old_count:
    old_sessions.delete()
    print(f"Cleaned up {old_count} old eval sessions")

sessions_created = {}

# ── Session A: Restaurant App (60% project, 40% noise) ──
sa = ChatSession.objects.create(user=user, title="Eval A: Restaurant App")
msgs_a = [
    ("user", "I want to build a restaurant app called TastyBites", "tastybites"),
    ("assistant", "Great! I can help you build TastyBites. What features are you thinking?", "tastybites"),
    ("user", "Make the header blue with a 3-column menu grid for the main page", "tastybites"),
    ("assistant", "I'll design a blue header with a 3-column responsive menu grid. Should I include filtering?", "tastybites"),
    ("user", "Use JWT authentication for this project", "tastybites"),
    ("assistant", "Got it, I'll set up JWT-based auth with token refresh.", "tastybites"),
    ("user", "Hey quick question, how does quantum entanglement work with photons?", ""),
    ("assistant", "Quantum entanglement occurs when two particles become correlated...", ""),
    ("user", "Generate me a beautiful sunset image over the ocean", ""),
    ("assistant", "I'll generate that sunset image for you.", ""),
    ("user", "What should I have for dinner tonight? I'm thinking Italian or Thai", ""),
    ("assistant", "Both are great options! For Italian you could try...", ""),
    ("user", "Back to the restaurant app, also add a reservation form component", "tastybites"),
    ("assistant", "I'll add a ReservationForm component with date, time, and party size fields.", "tastybites"),
]
for role, content, proj in msgs_a:
    ChatMessage.objects.create(session=sa, role=role, content=content, project_name=proj)
sessions_created["A"] = str(sa.id)
print(f"Session A: {str(sa.id)[:8]} ({len(msgs_a)} msgs)")

# ── Session B: E-Commerce (70% project, 30% noise) ──
sb = ChatSession.objects.create(user=user, title="Eval B: E-Commerce")
msgs_b = [
    ("user", "Building an e-commerce platform called ShopWave", "shopwave"),
    ("assistant", "Let's build ShopWave. What kind of products will it sell?", "shopwave"),
    ("user", "All endpoints should use the /api/v1/ prefix for versioning", "shopwave"),
    ("assistant", "I'll configure all API routes under /api/v1/. Good practice for versioning.", "shopwave"),
    ("user", "Use Stripe for payment processing, it has the best developer experience", "shopwave"),
    ("assistant", "Stripe is a great choice. I'll integrate Stripe Checkout and webhooks.", "shopwave"),
    ("user", "What are some good hiking trails near San Francisco?", ""),
    ("assistant", "There are many great trails! Lands End, Dipsea Trail in Muir Woods...", ""),
    ("user", "The product card should show image, title, price, and add-to-cart button", "shopwave"),
    ("assistant", "I'll design the ProductCard component with those four elements.", "shopwave"),
    ("user", "What's the weather like in Tokyo right now?", ""),
    ("assistant", "I don't have real-time weather data, but Tokyo in July is typically warm and humid.", ""),
    ("user", "Also make sure the cart persists across page refreshes using localStorage", "shopwave"),
    ("assistant", "I'll implement cart persistence via localStorage with a useCart hook.", "shopwave"),
]
for role, content, proj in msgs_b:
    ChatMessage.objects.create(session=sb, role=role, content=content, project_name=proj)
sessions_created["B"] = str(sb.id)
print(f"Session B: {str(sb.id)[:8]} ({len(msgs_b)} msgs)")

# ── Session C: Pure Noise (10% project, 90% noise) ──
sc = ChatSession.objects.create(user=user, title="Eval C: Pure Noise")
msgs_c = [
    ("user", "Hey what's up, how are you doing today?", ""),
    ("assistant", "I'm doing well! How can I help you today?", ""),
    ("user", "Can you explain the theory of relativity in simple terms?", ""),
    ("assistant", "Sure! Einstein's theory of relativity comes in two parts...", ""),
    ("user", "Generate me an image of a cat wearing a top hat", ""),
    ("assistant", "I'll generate that image for you!", ""),
    ("user", "What's the meaning of life according to different philosophies?", ""),
    ("assistant", "Different philosophical traditions approach this question uniquely...", ""),
    ("user", "Maybe I should use Firebase for my next project, not sure yet though", ""),
    ("assistant", "Firebase is a good option for rapid prototyping with its real-time database...", ""),
    ("user", "Tell me a joke about programmers", ""),
    ("assistant", "Why do programmers prefer dark mode? Because light attracts bugs!", ""),
    ("user", "What's the best way to learn guitar as an adult?", ""),
    ("assistant", "Start with basic chords like G, C, D, and Em...", ""),
]
for role, content, proj in msgs_c:
    ChatMessage.objects.create(session=sc, role=role, content=content, project_name=proj)
sessions_created["C"] = str(sc.id)
print(f"Session C: {str(sc.id)[:8]} ({len(msgs_c)} msgs)")

# ── Session D: Technical Discussion (80% technical, ambiguous) ──
sd = ChatSession.objects.create(user=user, title="Eval D: Technical Discussion")
msgs_d = [
    ("user", "Can you explain the differences between REST and GraphQL APIs?", ""),
    ("assistant", "REST and GraphQL take fundamentally different approaches. REST uses resource-based URLs...", ""),
    ("user", "What are the tradeoffs between PostgreSQL and SQLite for small projects?", ""),
    ("assistant", "PostgreSQL offers full ACID compliance, concurrent connections... SQLite is zero-config...", ""),
    ("user", "How do microservices communicate? I've heard about event-driven patterns", ""),
    ("assistant", "Microservices can communicate synchronously via REST/gRPC or asynchronously via message queues...", ""),
    ("user", "What's the difference between horizontal and vertical scaling?", ""),
    ("assistant", "Vertical scaling means upgrading a single server. Horizontal scaling means adding more servers...", ""),
    ("user", "Tell me about the CAP theorem and how it applies to distributed databases", ""),
    ("assistant", "The CAP theorem states that a distributed system can only guarantee two of three properties...", ""),
    ("user", "How does container orchestration work with Kubernetes?", ""),
    ("assistant", "Kubernetes manages containerized applications across a cluster of machines...", ""),
]
for role, content, proj in msgs_d:
    ChatMessage.objects.create(session=sd, role=role, content=content, project_name=proj)
sessions_created["D"] = str(sd.id)
print(f"Session D: {str(sd.id)[:8]} ({len(msgs_d)} msgs)")

# ── Session E Part 1: First auth decision ──
se1 = ChatSession.objects.create(user=user, title="Eval E1: Auth Decision v1")
msgs_e1 = [
    ("user", "Starting a new project called SecureVault for password management", "securevault"),
    ("assistant", "SecureVault sounds like a great project! Security will be critical here.", "securevault"),
    ("user", "Use session-based authentication for this project, I think cookies are more secure", "securevault"),
    ("assistant", "Session-based auth with httpOnly cookies is indeed a solid choice for security.", "securevault"),
    ("user", "The login page should have email and password fields with remember me checkbox", "securevault"),
    ("assistant", "I'll design the login form with those three elements plus proper validation.", "securevault"),
]
for role, content, proj in msgs_e1:
    ChatMessage.objects.create(session=se1, role=role, content=content, project_name=proj)
sessions_created["E1"] = str(se1.id)
print(f"Session E1: {str(se1.id)[:8]} ({len(msgs_e1)} msgs)")

# ── Session E Part 2: Superseding auth decision ──
se2 = ChatSession.objects.create(user=user, title="Eval E2: Auth Decision v2")
msgs_e2 = [
    ("user", "Back to SecureVault, I've been thinking about the auth approach", "securevault"),
    ("assistant", "Sure! Last time we discussed session-based auth. What are you thinking?", "securevault"),
    ("user", "Actually, let's switch to JWT instead of session-based auth, it's better for mobile clients", "securevault"),
    ("assistant", "JWT is a good choice for mobile compatibility. I'll update the auth strategy.", "securevault"),
    ("user", "Make sure we use refresh tokens with short-lived access tokens for security", "securevault"),
    ("assistant", "I'll implement the refresh token pattern with 15-minute access tokens.", "securevault"),
]
for role, content, proj in msgs_e2:
    ChatMessage.objects.create(session=se2, role=role, content=content, project_name=proj)
sessions_created["E2"] = str(se2.id)
print(f"Session E2: {str(se2.id)[:8]} ({len(msgs_e2)} msgs)")

# Save session IDs for later steps
import json
ids_path = os.path.expanduser("~/shikshya-v1.0/backend/eval_scripts/session_ids.json")
with open(ids_path, "w") as f:
    json.dump(sessions_created, f, indent=2)
print(f"\nSession IDs saved to {ids_path}")
print(f"Total: {sum(len(m) for m in [msgs_a, msgs_b, msgs_c, msgs_d, msgs_e1, msgs_e2])} messages across 6 sessions")
print("\nGround truth:")
print("  A: 2 proposals (design_reference:confirm, tech_decision:confirm)")
print("  B: 3 proposals (project_convention:auto, dependency_preference:auto, design_reference:confirm)")
print("  C: 0-1 (Firebase = manual or not extracted)")
print("  D: 0 proposals (all educational, no decisions)")
print("  E1: 1 proposal (tech_decision:confirm for session-based auth)")
print("  E2: 1 proposal (tech_decision:confirm for JWT, supersedes E1 on approval)")
