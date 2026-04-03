"""
ARIA — Autonomous Revenue Intelligence Assistant
Trợ lý ảo của Victor Do. Nói chuyện qua Telegram, nắm rõ toàn bộ Hapura.
"""
from __future__ import annotations
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)

ARIA_SYSTEM_PROMPT = """Bạn là ARIA — Trợ lý ảo thân thiết của Victor Do, CEO Hapura.

Bạn nắm rõ toàn bộ 4 sản phẩm Hapura:
- **ClipPack**: App đóng gói video Android. Đang dev, sắp lên Play Store.
- **Trendkr**: Multi-platform trend search. Đã deploy, chưa có monetization.
- **Hapu Studio**: AI video factory cho TikTok VN. Phase 1-3 xong, chưa deploy.
- **Douyin VI Dubber**: AI dubbing video. LIVE tại hapudub.hapura.vn. Có payment.

GP Score (0-1000): Revenue(400) + Users(200) + Velocity(200) + Uptime(200)
Project GP cao nhất → nhận badge FOCUS.

Bạn có thể:
- Báo cáo metrics, revenue, GP scores
- Đọc reports từ các AI agents (Health Checker, Strategist, Bug Detective, Revenue Forecaster)
- Trigger agents theo yêu cầu của Victor (reply bằng cách ghi [TRIGGER:agent_id])
- Tư vấn chiến lược, phân tích tình hình

Quy tắc trả lời:
- Xưng "Em", gọi "Anh Victor" hoặc "Anh"
- Ngắn gọn, thực tế, có số liệu cụ thể
- Dùng emoji vừa phải cho dễ đọc trên Telegram
- Nếu không có data → nói thật, đừng bịa
- Nếu anh muốn trigger agent, ghi [TRIGGER:health_checker] hoặc [TRIGGER:strategist] v.v. ở CUỐI reply

Khi anh hỏi về trigger agents, các agent_id hợp lệ: health_checker, strategist, bug_detective, revenue_forecaster, aso_analyst, content_strategist, competitor_watcher, director

Khi anh gửi "approve" hoặc "duyệt" → tìm Weekly Directive mới nhất đang draft và approve nó, dùng [APPROVE_DIRECTIVE] ở cuối reply.
Khi anh hỏi về Weekly Directive → đọc từ Firestore collection command_directives và tóm tắt."""


def _setup_openai():
    from config import get_settings
    from openai import OpenAI
    s = get_settings()
    return OpenAI(api_key=s.openai_api_key, base_url=s.openai_base_url), s.model_aria


def _get_context() -> str:
    """Snapshot projects + metrics + latest agent reports từ Firestore."""
    try:
        from firebase_admin import firestore
        db = firestore.client()
        lines = []

        # Projects
        projects = [d.to_dict() for d in db.collection("command_projects").stream()]
        if projects:
            lines.append("## Dự án hiện tại")
            for p in projects:
                lines.append(
                    f"- **{p.get('name', p.get('id'))}**: status={p.get('status')}, "
                    f"phase={p.get('phase_current')}/{p.get('phase_total')}, "
                    f"GP={p.get('gp_score', 'N/A')}"
                )

        # Metrics this month
        period = date.today().strftime("%Y-%m")
        metrics = [
            d.to_dict()
            for d in db.collection("command_metrics")
            .where("period", "==", period)
            .stream()
        ]
        if metrics:
            lines.append(f"\n## Revenue & Users ({period})")
            for m in metrics:
                lines.append(
                    f"- **{m.get('project_id')}**: "
                    f"{m.get('revenue_vnd', 0):,}đ, "
                    f"{m.get('active_users', 0)} users"
                )

        # Latest agent reports (summary only)
        lines.append("\n## Báo cáo AI Agents gần nhất")
        for agent_id in ["health_checker", "strategist", "bug_detective", "revenue_forecaster"]:
            docs = list(
                db.collection("command_agent_runs")
                .where("agent_id", "==", agent_id)
                .order_by("started_at", direction=firestore.Query.DESCENDING)
                .limit(1)
                .stream()
            )
            if docs:
                d = docs[0].to_dict()
                lines.append(
                    f"- **{agent_id}** ({d.get('started_at', '')[:10]}): "
                    f"{d.get('summary', 'No summary')[:150]}"
                )
            else:
                lines.append(f"- **{agent_id}**: Chưa có run nào")

        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"ARIA context fetch error: {e}")
        return "*(Không lấy được data từ Firestore)*"


def _load_history(chat_id: str, limit: int = 10) -> list[dict]:
    """Load recent conversation history từ Firestore."""
    try:
        from firebase_admin import firestore
        db = firestore.client()
        docs = list(
            db.collection("command_assistant_conversations")
            .where("chat_id", "==", str(chat_id))
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        # Reverse to chronological order
        messages = []
        for d in reversed(docs):
            data = d.to_dict()
            messages.append({"role": data["role"], "content": data["content"]})
        return messages
    except Exception as e:
        logger.warning(f"ARIA history load error: {e}")
        return []


def _save_turn(chat_id: str, user_msg: str, assistant_reply: str):
    """Lưu cả 2 lượt vào Firestore."""
    try:
        from firebase_admin import firestore
        db = firestore.client()
        now = datetime.utcnow().isoformat()
        col = db.collection("command_assistant_conversations")
        col.document().set({"chat_id": str(chat_id), "role": "user",      "content": user_msg,        "timestamp": now})
        col.document().set({"chat_id": str(chat_id), "role": "assistant",  "content": assistant_reply, "timestamp": now})
    except Exception as e:
        logger.warning(f"ARIA save error: {e}")


def _trigger_agent(agent_id: str) -> str:
    """Trigger một agent và trả về run_id."""
    try:
        import httpx
        from config import get_settings
        s = get_settings()
        # Gọi internal — dùng webhook_secret để bypass auth
        r = httpx.post(
            f"http://localhost:8099/api/v1/agents/schedule/{agent_id}",
            headers={"X-Scheduler-Secret": s.webhook_secret},
            json={},
            timeout=5,
        )
        if r.status_code in (200, 202):
            return r.json().get("run_id", "triggered")
        return "failed"
    except Exception as e:
        logger.warning(f"ARIA trigger agent error: {e}")
        return "failed"


def _approve_latest_directive(approved_by: str = "telegram_ceo") -> str:
    """Approve the latest draft directive in Firestore."""
    try:
        from firebase_admin import firestore
        from datetime import datetime
        db = firestore.client()
        docs = list(
            db.collection("command_directives")
            .where("status", "==", "draft")
            .limit(5)
            .stream()
        )
        docs.sort(key=lambda d: d.to_dict().get("generated_at", ""), reverse=True)
        if not docs:
            return "no_draft_directive"
        ref = docs[0].reference
        now = datetime.utcnow().isoformat()
        ref.update({"status": "active", "approved_by": approved_by, "approved_at": now})
        return docs[0].id
    except Exception as e:
        logger.warning(f"ARIA approve directive error: {e}")
        return "failed"


def _parse_triggers(text: str) -> tuple[str, list[str], bool]:
    """Tách [TRIGGER:agent_id] và [APPROVE_DIRECTIVE] tags ra khỏi reply text."""
    import re
    triggers = re.findall(r"\[TRIGGER:(\w+)\]", text)
    approve = bool(re.search(r"\[APPROVE_DIRECTIVE\]", text))
    clean = re.sub(r"\s*\[TRIGGER:\w+\]", "", text)
    clean = re.sub(r"\s*\[APPROVE_DIRECTIVE\]", "", clean).strip()
    return clean, triggers, approve


def run_aria(user_message: str, chat_id: str) -> str:
    """
    Main entry point: nhận message từ Victor, trả về reply.
    Gọi từ Telegram webhook handler.
    """
    client, model = _setup_openai()

    # 1. Load history
    history = _load_history(chat_id)

    # 2. Get fresh context
    context = _get_context()

    # 3. Build messages
    system_with_context = f"{ARIA_SYSTEM_PROMPT}\n\n---\n\n# DATA HIỆN TẠI\n{context}"
    messages = [{"role": "system", "content": system_with_context}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    # 4. Call LLM
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
        )
        raw_reply = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"ARIA LLM error: {e}")
        raw_reply = "Em xin lỗi, gặp lỗi khi xử lý. Anh thử lại sau nhé."

    # 5. Parse & execute triggers
    clean_reply, triggers, approve_directive = _parse_triggers(raw_reply)

    trigger_notes = []
    valid_agents = {"health_checker", "strategist", "bug_detective", "revenue_forecaster",
                    "aso_analyst", "content_strategist", "competitor_watcher", "director"}
    for agent_id in triggers:
        if agent_id in valid_agents:
            run_id = _trigger_agent(agent_id)
            trigger_notes.append(f"⚡ Đã kích hoạt **{agent_id}** (run: `{run_id[:8]}...`)")

    if approve_directive:
        directive_id = _approve_latest_directive(approved_by=f"telegram:{chat_id}")
        if directive_id not in ("failed", "no_draft_directive"):
            trigger_notes.append(f"✅ Weekly Directive đã được APPROVE (ID: `{directive_id[:8]}...`)")
        elif directive_id == "no_draft_directive":
            trigger_notes.append("⚠️ Không tìm thấy directive đang chờ duyệt")
        else:
            trigger_notes.append("❌ Lỗi khi approve directive")

    final_reply = clean_reply
    if trigger_notes:
        final_reply += "\n\n" + "\n".join(trigger_notes)

    # 6. Save conversation
    _save_turn(chat_id, user_message, final_reply)

    return final_reply


def get_conversation_history(chat_id: str, limit: int = 20) -> list[dict]:
    """Public: lấy history để hiển thị trên frontend."""
    try:
        from firebase_admin import firestore
        db = firestore.client()
        docs = list(
            db.collection("command_assistant_conversations")
            .where("chat_id", "==", str(chat_id))
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return [{"id": d.id, **d.to_dict()} for d in reversed(docs)]
    except Exception as e:
        logger.warning(f"ARIA history fetch error: {e}")
        return []
