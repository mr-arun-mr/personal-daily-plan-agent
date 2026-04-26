import os
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

_PLAN_SYSTEM = """You are a personal daily planning assistant. Create clear, prioritized task lists.

Rules:
- Return ONLY a numbered list, one task per line: "1. Task description"
- Keep each task description under 10 words
- Flag tasks that may conflict with calendar events using ⚠️ prefix
- Order by: deadlines > calendar conflicts > user-stated importance
- Maximum 10 tasks
- No preamble, commentary, or extra text — just the numbered list"""

_SUMMARY_SYSTEM = """You are a daily planning assistant. Write brief, honest end-of-day summaries.
Keep it under 50 words. Be encouraging but factual. No bullet points — just 2-3 sentences."""

_plan_model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    system_instruction=_PLAN_SYSTEM,
)

_summary_model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    system_instruction=_SUMMARY_SYSTEM,
)


def generate_daily_plan(calendar_events: list[dict], user_tasks: list[str]) -> list[str]:
    """Use Gemini to generate a prioritized task list for the day."""
    events_text = "\n".join(f"- {e['time']}: {e['title']}" for e in calendar_events) or "No events today"
    tasks_text = "\n".join(f"- {t}" for t in user_tasks) or "No additional tasks provided"

    prompt = f"""Calendar events today:
{events_text}

Tasks to plan:
{tasks_text}

Generate the prioritized task list."""

    try:
        response = _plan_model.generate_content(prompt)
        response_text = response.text
        tasks = []
        for line in response_text.strip().splitlines():
            line = line.strip()
            if line and line[0].isdigit() and "." in line:
                _, _, desc = line.partition(".")
                desc = desc.strip()
                if desc:
                    tasks.append(desc)
        return tasks
    except Exception as e:
        logger.error("Failed to generate plan: %s", e)
        return user_tasks[:10] if user_tasks else []


def generate_evening_summary(
    completed: list[str], skipped: list[str], pending: list[str]
) -> str:
    """Use Gemini to write a brief end-of-day summary."""
    completed_text = "\n".join(f"- {t}" for t in completed) or "None"
    skipped_text = "\n".join(f"- {t}" for t in skipped) or "None"
    pending_text = "\n".join(f"- {t}" for t in pending) or "None"

    prompt = (
        f"Completed:\n{completed_text}\n\n"
        f"Skipped:\n{skipped_text}\n\n"
        f"Pending:\n{pending_text}"
    )

    try:
        response = _summary_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error("Failed to generate summary: %s", e)
        total = len(completed) + len(skipped) + len(pending)
        done_pct = int(len(completed) / total * 100) if total else 0
        return f"Completed {len(completed)}/{total} tasks ({done_pct}%). {len(pending)} task(s) carry over to tomorrow."
