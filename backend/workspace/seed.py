"""
Workspace Seed — Initialize WorkspaceConfig documents in Firestore.
Run once per product to set up the AI Workplace configuration.

Usage:
  cd backend && python -c "from workspace.seed import seed_all; seed_all()"
"""
from __future__ import annotations
from datetime import datetime


CLIPPACK_CONFIG = {
    "product_id": "clippack",
    "product_name": "ClipPack",
    "platform": "android",
    "enabled_departments": [
        "executive", "growth", "product", "revenue", "support", "analytics", "infra"
    ],
    "enabled_agents": {
        "executive":  ["hq_assistant", "director"],
        "growth":     ["aso_analyst", "content_strategist", "competitor_watcher"],
        "product":    ["bug_detective", "health_checker", "feature_prioritizer", "release_planner"],
        "revenue":    ["revenue_forecaster", "pricing_strategist", "conversion_analyst"],
        "support":    ["review_monitor", "retention_analyst", "support_draft"],
        "analytics":  ["strategist", "anomaly_detector", "dashboard_curator"],
        "infra":      ["infra_monitor", "cost_optimizer"],
    },
    "data_sources": {
        "playstore": {
            "package_name": "com.hapura.clippack",
            "note": "Google Play Developer API — configure service account for live data",
        },
        "github": {
            "repo": "hapuragroup/clippack",
            "note": "Set GITHUB_TOKEN in .env for higher rate limits",
        },
        "firebase": {
            "project": "trendkr-hapura",
            "note": "Same Firebase project, namespace command_*",
        },
    },
    "schedule_overrides": {
        "aso_analyst":        "0 9 * * 1",    # Monday 9am
        "competitor_watcher": "0 10 * * 3",   # Wednesday 10am
        "content_strategist": "0 11 * * 3",   # Wednesday 11am
        "review_monitor":     "0 9 * * *",    # Daily 9am
        "anomaly_detector":   "*/30 * * * *", # Every 30 min
        "dashboard_curator":  "0 */4 * * *",  # Every 4 hours
        "director":           "0 9 * * 2",    # Tuesday 9am
        "pricing_strategist": "0 9 1 * *",    # 1st of month
        "cost_optimizer":     "0 9 1 * *",    # 1st of month
    },
    "llm_overrides": {
        "director":           "aws/claude-opus-4-6",
        "revenue_forecaster": "aws/claude-opus-4-6",
        "health_checker":     "aws/claude-haiku-4-5",
        "infra_monitor":      "aws/claude-haiku-4-5",
    },
    "meta": {
        "description": "ClipPack — Android video clip subscription app",
        "goal": "Grow to 10,000 MAU and 300 paid subscribers by end of 2026",
        "current_phase": "Subscription model development + ASO optimization",
    },
    "created_at": datetime.utcnow().isoformat(),
    "updated_at": datetime.utcnow().isoformat(),
}


TRENDKR_CONFIG = {
    "product_id": "trendkr",
    "product_name": "Trendkr",
    "platform": "web",
    "enabled_departments": [
        "executive", "product", "revenue", "analytics", "infra"
    ],
    "enabled_agents": {
        "executive":  ["hq_assistant", "director"],
        "product":    ["bug_detective", "health_checker", "feature_prioritizer"],
        "revenue":    ["revenue_forecaster", "pricing_strategist"],
        "analytics":  ["strategist", "anomaly_detector"],
        "infra":      ["infra_monitor"],
    },
    "data_sources": {
        "web_analytics": {
            "note": "Firebase Analytics / Google Analytics — configure for web",
        },
        "github": {
            "repo": "hapuragroup/trendkr",
        },
    },
    "schedule_overrides": {},
    "llm_overrides": {
        "director": "aws/claude-opus-4-6",
    },
    "meta": {
        "description": "Trendkr — Web trend monitoring platform",
        "goal": "Monetization phase — convert free users to paid",
        "current_phase": "Phase 4 — monetization",
    },
    "created_at": datetime.utcnow().isoformat(),
    "updated_at": datetime.utcnow().isoformat(),
}


def seed_product(config: dict) -> str:
    """Seed a single product workspace config. Returns product_id."""
    from api.deps import get_firebase_app
    get_firebase_app()
    from firebase_admin import firestore
    db = firestore.client()
    product_id = config["product_id"]
    db.collection("command_workspace_config").document(product_id).set(config, merge=True)
    print(f"  Seeded workspace config for: {product_id}")
    return product_id


def seed_departments() -> None:
    """Seed department metadata into Firestore."""
    from api.deps import get_firebase_app
    get_firebase_app()
    from firebase_admin import firestore
    from workspace.registry import DEPARTMENTS
    db = firestore.client()
    for dept_id, dept in DEPARTMENTS.items():
        db.collection("command_departments").document(dept_id).set(
            dept.model_dump(), merge=True
        )
        print(f"  Seeded department: {dept_id}")


def seed_all() -> None:
    """Seed all workspace configs and department metadata."""
    print("Seeding AI Workplace...")
    seed_departments()
    seed_product(CLIPPACK_CONFIG)
    seed_product(TRENDKR_CONFIG)
    print("\nSeed complete! AI Workplace ready.")
    print("\nDepartments: 7")
    print("Products configured: clippack, trendkr")
    print("\nNext steps:")
    print("  1. Start backend: uvicorn main:app --port 8099 --reload")
    print("  2. Start frontend: npm run dev  (port 5199)")
    print("  3. Visit http://localhost:5199/workplace")
    print("  4. Trigger Growth department to test ASO + Content agents")


if __name__ == "__main__":
    seed_all()
