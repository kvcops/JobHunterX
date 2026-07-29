"""
Vellum OS — Browser Execution Agent (Agent B)

Uses browser-use with ChatLiteLLM for form filling.
Robust HITL state machine for login, CAPTCHA, MFA, complex forms.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from vellum.config.logging import get_logger
from vellum.config import database as db
from vellum.config.settings import get_settings, Settings
from vellum.models import AgentEvent, HITLType

log = get_logger("browser_agent")

# A realistic, non-headless-looking desktop User-Agent.
# Cloudflare flags the default Playwright/automation UA very quickly.
_STEALTH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# Persistent profile path reused across runs. A stable profile accumulates
# cookies, localStorage and an auth "history" that Cloudflare scores as a
# real returning user rather than a fresh headless instance.
_STEALTH_USER_DATA_DIR = Path("./data/browser_profile")


# ---------------------------------------------------------------------------
# HITL state detection heuristics
# ---------------------------------------------------------------------------

LOGIN_INDICATORS = [
    "sign in", "log in", "login", "email address", "password",
    "forgot password", "create account", "register",
]

CAPTCHA_INDICATORS = [
    "captcha", "recaptcha", "hcaptcha", "verify you are human",
    "i'm not a robot", "turnstile",
]

MFA_INDICATORS = [
    "verification code", "otp", "two-factor", "2fa",
    "authenticator", "verify your identity",
]


def _detect_page_type(page_text: str) -> str:
    """Detect if the page requires special handling.

    Returns: "simple_form", "login_required", "captcha_detected",
             "mfa_required", "complex_form", or "unknown".
    """
    text_lower = page_text.lower()

    for indicator in CAPTCHA_INDICATORS:
        if indicator in text_lower:
            return "captcha_detected"

    for indicator in MFA_INDICATORS:
        if indicator in text_lower:
            return "mfa_required"

    for indicator in LOGIN_INDICATORS:
        if indicator in text_lower:
            return "login_required"

    return "simple_form"


# ---------------------------------------------------------------------------
# Stealth browser profile builder (Cloudflare / bot-detection mitigation)
# ---------------------------------------------------------------------------

def _build_stealth_profile(settings: Settings) -> Any:
    """Build a BrowserProfile tuned to evade Cloudflare / bot detection.

    Strategy (tiered):
      1. If BROWSER_USE_API_KEY is set -> use the browser-use cloud browser,
         which provides managed stealth fingerprinting + residential proxy
         rotation. This is the only reliable way past Cloudflare Turnstile.
      2. Otherwise -> local stealth profile:
         - Persistent user_data_dir (cookies/history accumulate trust).
         - headless=False when allowed (old headless is trivially detected;
           the new Chromium headless still leaks many fingerprints).
         - Realistic User-Agent and locale.
         - Default anti-tracking extensions (uBlock, cookie banner) enabled:
           these reduce the tracking signals that feed bot-scoring.
    """
    from browser_use import BrowserProfile

    use_cloud = bool(os.getenv("BROWSER_USE_API_KEY")) and bool(getattr(settings, "browser_use_cloud", False))

    if use_cloud:
        log.info("browser_profile_cloud", reason="BROWSER_USE_API_KEY present + cloud enabled")
        return BrowserProfile(
            use_cloud=True,
            user_agent=_STEALTH_USER_AGENT,
            captcha_solver=True,
        )

    # Local stealth profile
    try:
        _STEALTH_USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    return BrowserProfile(
        headless=settings.browser_use_headless,
        user_data_dir=str(_STEALTH_USER_DATA_DIR.resolve()),
        user_agent=_STEALTH_USER_AGENT,
        viewport={"width": 1920, "height": 1080},
        enable_default_extensions=False,  # DISABLED: extension downloads from Chrome Web Store hang on Windows, blocking CDP
        disable_security=False,
        captcha_solver=True,
        keep_alive=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process,AutomationControlled",
            "--disable-popup-blocking",
            "--no-first-run",
            "--no-default-browser-check",
        ],
    )


# ---------------------------------------------------------------------------
# Browser agent runner
# ---------------------------------------------------------------------------

_active_sessions: list[Any] = []

# Registry of paused browser sessions. When the agent hits CAPTCHA/login/MFA,
# the session is moved here instead of being destroyed, keeping the browser
# window alive for user intervention. Keyed by job_id.
_paused_sessions: dict[str, dict] = {}

# Registry of takeover gates keyed by job_id. Allows the API layer to pause/
# resume the URL streamer (and signal the agent to yield) when the user takes
# over the live browser window. Each value is an asyncio.Event.
_takeover_gates: dict[str, asyncio.Event] = {}


def register_takeover_gate(job_id: str, gate: asyncio.Event) -> None:
    _takeover_gates[job_id] = gate


def _set_gate_threadsafe(job_id: str, value: bool) -> None:
    """Set the takeover gate for a job from any thread (still threadsafe just in case)."""
    gate = _takeover_gates.get(job_id)
    if gate is None:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = gate._loop if hasattr(gate, "_loop") else None  # type: ignore[attr-defined]
    if loop is None:
        return
    def _flip():
        if value:
            gate.set()
        else:
            gate.clear()
    try:
        loop.call_soon_threadsafe(_flip)
    except RuntimeError:
        pass


def pause_streaming(job_id: str) -> None:
    """User took over the browser window — pause URL broadcasts AND agent actions."""
    _set_gate_threadsafe(job_id, False)
    # Also pause the browser-use Agent so it stops taking steps
    _pause_active_agent()


def resume_streaming(job_id: str) -> None:
    """User finished manual control — resume URL broadcasts AND agent actions."""
    _set_gate_threadsafe(job_id, True)
    # Also resume the browser-use Agent
    _resume_active_agent()


def _pause_active_agent() -> None:
    """Pause the active browser-use Agent (stops executing steps)."""
    for agent in _active_sessions:
        if hasattr(agent, "pause") and hasattr(agent, "_external_pause_event"):
            try:
                agent.state.paused = True
                agent._external_pause_event.clear()
                log.info("agent_paused", session_id=getattr(agent, "session_id", ""))
            except Exception as exc:
                log.warning("agent_pause_failed", error=str(exc))


def _resume_active_agent() -> None:
    """Resume the active browser-use Agent (resumes executing steps)."""
    for agent in _active_sessions:
        if hasattr(agent, "resume") and hasattr(agent, "_external_pause_event"):
            try:
                agent.state.paused = False
                agent._external_pause_event.set()
                log.info("agent_resumed", session_id=getattr(agent, "session_id", ""))
            except Exception as exc:
                log.warning("agent_resume_failed", error=str(exc))


def get_active_cdp_url() -> str:
    """Return the CDP websocket URL of the currently active browser, if any."""
    for agent in _active_sessions:
        sess = getattr(agent, "browser_session", None)
        if sess is not None:
            cdp = getattr(sess, "cdp_url", "") or ""
            if cdp:
                return cdp
    return ""


def get_active_browser_session() -> Any:
    """Return the active BrowserSession object, or None."""
    for agent in _active_sessions:
        sess = getattr(agent, "browser_session", None)
        if sess is not None:
            return sess
    return None


async def get_active_page() -> Any:
    """Return the current Playwright Page of the active browser, or None."""
    sess = get_active_browser_session()
    if sess is None:
        return None
    try:
        return await sess.get_current_page()
    except Exception:
        return None


async def stop_all_active_browsers():
    """Halt any active browser-use Agent sessions immediately."""
    log.info("stopping_all_active_browsers", count=len(_active_sessions))
    for agent in list(_active_sessions):
        try:
            if hasattr(agent, "stop"):
                agent.stop()
            if hasattr(agent, "browser_session") and agent.browser_session:
                try:
                    await agent.browser_session.close()
                except Exception:
                    pass
            elif hasattr(agent, "browser") and agent.browser:
                try:
                    await agent.browser.close()
                except Exception:
                    pass
        except Exception as exc:
            log.warning("error_triggering_browser_close", error=str(exc))
    _active_sessions.clear()
    _paused_sessions.clear()



def save_paused_session(job_id: str, reason: str, url: str = "") -> None:
    """Save a browser session as paused when CAPTCHA/login/MFA is detected.
    
    The session stays alive — the browser window remains open for the user
    to manually intervene. The agent stops executing steps.
    """
    _paused_sessions[job_id] = {
        "reason": reason,
        "url": url,
        "status": "paused",
    }
    log.info("session_paused", job_id=job_id, reason=reason)


def get_paused_sessions() -> dict[str, dict]:
    """Return all currently paused browser sessions."""
    return dict(_paused_sessions)


def clear_paused_session(job_id: str) -> None:
    """Remove a paused session entry after the user resolves it."""
    _paused_sessions.pop(job_id, None)


async def run(state: dict) -> dict:
    """Agent B: Browser execution for job application.

    Input state: {"job": dict, "profile": dict, "tailored_pdf": bytes}
    Output: updates with browser_result, hitl_request (if needed), events

    Uses LangGraph interrupt() for HITL pauses.
    """
    job = state.get("job", {})
    profile = state.get("profile", {})
    tailored_pdf = state.get("tailored_pdf")
    job_id = job.get("id", "")
    apply_url = job.get("apply_url") or job.get("career_page_url", "")
    events: list[dict] = []
    errors: list[str] = []

    if not apply_url:
        events.append(AgentEvent(
            agent="browser_agent",
            event_type="error",
            job_id=job_id,
            message="No apply URL available",
        ).model_dump(mode="json"))
        return {"browser_result": {"status": "no_url"}, "events": events, "errors": errors}

    events.append(AgentEvent(
        agent="browser_agent",
        event_type="progress",
        job_id=job_id,
        message=f"Opening application page: {apply_url}",
    ).model_dump(mode="json"))

    await db.update_job(job_id, status="applying")

    settings = get_settings()

    # Save tailored PDF to temp file if available, named after candidate+company
    pdf_path = None
    if tailored_pdf:
        screenshots_dir = settings.screenshots_full_path / job_id
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        import re as _re
        def _slug(s):
            return _re.sub(r"[^A-Za-z0-9_\-]", "", (s or "").strip().replace(" ", "_"))[:40]
        cand = _slug(profile.get("name", ""))
        comp = _slug(job.get("company", ""))
        fname = "_".join(p for p in [cand, comp] if p) or "tailored_resume"
        pdf_path = screenshots_dir / f"{fname}.pdf"
        pdf_path.write_bytes(tailored_pdf)

    try:
        # --- Initialize browser-use Agent with our LLM ---
        from browser_use import Agent, Controller, ActionResult
        from browser_use.browser import BrowserSession
        from browser_use.llm.litellm import ChatLiteLLM
        try:
            from browser_use import BrowserProfile
        except ImportError:
            BrowserProfile = None

        controller = Controller()

        @controller.action("Upload candidate resume file (PDF/CV) to application form input")
        async def upload_resume_file(browser_session) -> ActionResult:
            """Robustly locate a file input on the page and upload the resume PDF.

            Strategy (in order):
              1. Any <input type="file"> on the page (visible or hidden) — set files directly.
              2. Click an upload/resume/attach control and intercept the file chooser dialog.
            Never clicks ambiguous text-matched elements to avoid mis-targeting.
            """
            if not pdf_path or not pdf_path.exists():
                return ActionResult(error="Resume PDF file path not found")
            resolved = str(pdf_path.resolve())
            try:
                page = await browser_session.get_current_page()

                # 1) Direct <input type="file"> — the reliable path.
                file_inputs = page.locator("input[type='file']")
                count = await file_inputs.count()
                for idx in range(count):
                    try:
                        fi = file_inputs.nth(idx)
                        # Some inputs are hidden but still accept set_input_files.
                        await fi.set_input_files(resolved)
                        return ActionResult(extracted_content=f"Successfully attached resume PDF ({pdf_path.name}) to file input #{idx + 1}.")
                    except Exception:
                        continue

                # 2) File-chooser interception via upload-trigger elements.
                #    Use precise, resume-specific selectors only (no generic "Attach"/"Account").
                trigger_selectors = [
                    "label:has-text('Resume')",
                    "label:has-text('CV')",
                    "button:has-text('Upload Resume')",
                    "button:has-text('Upload CV')",
                    "button:has-text('Attach Resume')",
                    "[class*='resume' i][class*='upload' i]",
                    "[data-testid*='resume' i]",
                    "input[type='file']",
                ]
                for sel in trigger_selectors:
                    loc = page.locator(sel).first
                    if await loc.count() == 0:
                        continue
                    try:
                        async with page.expect_file_chooser(timeout=5000) as fc_info:
                            await loc.click(force=True, timeout=3000)
                        chooser = await fc_info.value
                        await chooser.set_files(resolved)
                        return ActionResult(extracted_content=f"Successfully uploaded resume PDF via chooser (selector: {sel}).")
                    except Exception:
                        continue

                return ActionResult(error="No file upload input or resume upload trigger found on page. Skipping resume upload.")
            except Exception as exc:
                return ActionResult(error=f"Upload execution error: {str(exc)}")

        @controller.action("Select a dropdown/select option by clicking the option with matching text")
        async def select_dropdown_option(browser_session, index: int, text: str) -> ActionResult:
            """Select an option from a dropdown menu.

            Handles:
              - Native <select> elements
              - Custom dropdowns (React Select, Material UI, Chakra UI)
              - ARIA combobox/listbox menus
              - Click-to-open dropdown panels

            Strategy:
              1. If it's a native <select>, use select_option(label=text).
              2. For custom dropdowns, click to open, then click the matching option.
              3. For ARIA combobox, type to filter then click the match.
            """
            try:
                page = await browser_session.get_current_page()
                element = await page.query_selector(f"[data-index='{index}']")
                if not element:
                    element = await page.query_selector(f":nth-child({index})")
                if not element:
                    return ActionResult(error=f"Element with index {index} not found")

                tag = await element.evaluate("el => el.tagName.toLowerCase()")
                role = await element.evaluate("el => el.getAttribute('role') || ''")

                # Strategy 1: Native <select> element
                if tag == "select":
                    await element.select_option(label=text)
                    return ActionResult(extracted_content=f"Selected '{text}' from native <select> dropdown")

                # Strategy 2: ARIA combobox — type to filter, then click
                if role == "combobox" or await element.evaluate("el => el.getAttribute('aria-autocomplete') || ''"):
                    await element.click()
                    await page.keyboard.type(text, delay=50)
                    await page.wait_for_timeout(500)
                    # Click the matching option in the popup
                    option = page.locator(f"[role='option']:has-text('{text}'), [role='menuitem']:has-text('{text}'), li:has-text('{text}')").first
                    if await option.count() > 0:
                        await option.click()
                        return ActionResult(extracted_content=f"Selected '{text}' from combobox autocomplete")
                    # Fallback: press Enter
                    await page.keyboard.press("Enter")
                    return ActionResult(extracted_content=f"Typed '{text}' in combobox and pressed Enter")

                # Strategy 3: Custom dropdown — click to open, then click option
                await element.click()
                await page.wait_for_timeout(300)
                option = page.locator(f"[role='option']:has-text('{text}'), [role='menuitem']:has-text('{text}'), li:has-text('{text}'), div:has-text('{text}')").first
                if await option.count() > 0:
                    await option.click()
                    return ActionResult(extracted_content=f"Selected '{text}' from custom dropdown")

                return ActionResult(error=f"Could not find option '{text}' in dropdown at index {index}")
            except Exception as exc:
                return ActionResult(error=f"Dropdown selection error: {str(exc)}")

        @controller.action("Fill a date input field with a specific date")
        async def fill_date_field(browser_session, index: int, date_value: str) -> ActionResult:
            """Fill a date input field, handling multiple date picker formats.

            Supports:
              - HTML5 <input type="date"> — type ISO date directly
              - jQuery/Bootstrap datepickers — click input, type date, press Escape
              - Material UI / React date pickers — click, type, confirm
              - Custom calendar widgets — navigate year/month, click day cell

            Args:
                index: Element index from the page state
                date_value: Date in ISO format (YYYY-MM-DD) or US format (MM/DD/YYYY)
            """
            try:
                page = await browser_session.get_current_page()
                element = await page.query_selector(f"[data-index='{index}']")
                if not element:
                    return ActionResult(error=f"Date element with index {index} not found")

                input_type = await element.evaluate("el => el.type || el.getAttribute('type') || ''")
                placeholder = await element.evaluate("el => el.placeholder || ''")
                tag = await element.evaluate("el => el.tagName.toLowerCase()")

                # Determine the format to use
                if "yyyy" in placeholder.lower() or "mm/dd" in placeholder.lower():
                    # Parse ISO date and format as MM/DD/YYYY
                    parts = date_value.split("-")
                    if len(parts) == 3:
                        formatted = f"{parts[1]}/{parts[2]}/{parts[0]}"
                    else:
                        formatted = date_value
                else:
                    formatted = date_value

                # Strategy 1: HTML5 date input
                if input_type == "date" or tag == "input":
                    await element.click()
                    await element.evaluate("el => el.value = ''")
                    await page.keyboard.type(formatted, delay=30)
                    await page.keyboard.press("Tab")
                    return ActionResult(extracted_content=f"Filled date field with '{formatted}'")

                # Strategy 2: Click to open picker, then type
                await element.click()
                await page.wait_for_timeout(500)
                await page.keyboard.type(formatted, delay=30)
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(300)

                return ActionResult(extracted_content=f"Filled date field with '{formatted}'")
            except Exception as exc:
                return ActionResult(error=f"Date field error: {str(exc)}")

        @controller.action("Read verification code from email and return it")
        async def get_email_otp(email_address: str, sender_filter: str = "", timeout_seconds: int = 30) -> ActionResult:
            """Retrieve an OTP/verification code from the candidate's email inbox.

            Uses IMAP to poll for new emails matching the sender filter,
            extracts the 4-8 digit code, and returns it.

            Args:
                email_address: The email address to check
                sender_filter: Optional sender email/domain to filter by
                timeout_seconds: How long to wait for the OTP email
            """
            import imaplib
            import re
            import time as _time

            try:
                settings = get_settings()
                imap_host = "imap.gmail.com"
                email_pass = getattr(settings, "email_app_password", None)

                if not email_pass:
                    return ActionResult(error="Email app password not configured. Set EMAIL_APP_PASSWORD in .env")

                otp_pattern = re.compile(r'(?<!\d)(\d{4,8})(?!\d)')
                deadline = _time.time() + timeout_seconds

                while _time.time() < deadline:
                    try:
                        with imaplib.IMAP4_SSL(imap_host) as conn:
                            conn.login(email_address, email_pass)
                            conn.select("INBOX")

                            criteria = ['UNSEEN']
                            if sender_filter:
                                criteria.append(f'FROM "{sender_filter}"')
                            search_str = '(' + ' '.join(criteria) + ')'
                            _, msg_ids = conn.search(None, search_str)

                            if msg_ids[0]:
                                latest_id = msg_ids[0].split()[-1]
                                _, data = conn.fetch(latest_id, '(RFC822)')
                                msg = email.message_from_bytes(data[0][1])

                                body = ""
                                if msg.is_multipart():
                                    for part in msg.walk():
                                        if part.get_content_type() == "text/plain":
                                            payload = part.get_payload(decode=True)
                                            if payload:
                                                body = payload.decode(errors="ignore")
                                            break
                                else:
                                    payload = msg.get_payload(decode=True)
                                    if payload:
                                        body = payload.decode(errors="ignore")

                                match = otp_pattern.search(body)
                                if match:
                                    return ActionResult(extracted_content=f"OTP_CODE:{match.group(1)}")
                    except Exception:
                        pass
                    _time.sleep(2)

                return ActionResult(error=f"OTP not received within {timeout_seconds}s")
            except Exception as exc:
                return ActionResult(error=f"Email OTP error: {str(exc)}")

        # Use our LiteLLM router — gemma-4-31b-it avoids Gemini 3+ deprecation warnings
        # and supports temperature/top_p/top_k natively
        from vellum.config.settings import get_settings
        _settings = get_settings()

        _fallback_models = []
        if _settings.groq_api_key:
            _fallback_models.append("groq/openai/gpt-oss-20b")
        if _settings.mistral_api_key:
            _fallback_models.append("mistral/mistral-large-2512")
        if _settings.google_api_key:
            _fallback_models.append("gemini/gemini-3.1-flash-lite")

        llm = ChatLiteLLM(model="gemini/gemma-4-31b-it", fallbacks=_fallback_models if _fallback_models else None)

        # Build comprehensive candidate credential memory for the task
        # --- Education History ---
        edu_lines = []
        for ed in profile.get("education", []):
            grade_str = f", Grade: {ed.get('grade')}" if ed.get("grade") else ""
            details_str = f", {ed.get('details')}" if ed.get("details") else ""
            edu_lines.append(
                f"  • {ed.get('degree', '')} from {ed.get('institution', '')} ({ed.get('start', '')} – {ed.get('end', '')}){grade_str}{details_str}"
            )
        edu_block = "\n".join(edu_lines) if edu_lines else "  (Not provided)"

        # --- Work Experience History ---
        exp_lines = []
        for exp in profile.get("experience", []):
            bullets = exp.get("bullets", [])
            bullet_str = ""
            if bullets:
                bullet_str = "\n" + "\n".join(f"    - {b}" for b in bullets[:4])
            exp_lines.append(
                f"  • {exp.get('role', '')} at {exp.get('company', '')} ({exp.get('start', '')} – {exp.get('end', '')}){bullet_str}"
            )
        exp_block = "\n".join(exp_lines) if exp_lines else "  (Not provided)"

        # --- Application Q&A Memory ---
        qa_memory = profile.get("qa_memory", {})
        qa_lines = []
        if qa_memory.get("expected_salary"):
            qa_lines.append(f"  • Expected/Preferred Salary: {qa_memory['expected_salary']}")
        if qa_memory.get("current_ctc"):
            qa_lines.append(f"  • Current CTC: {qa_memory['current_ctc']}")
        if qa_memory.get("expected_ctc"):
            qa_lines.append(f"  • Expected CTC: {qa_memory['expected_ctc']}")
        if qa_memory.get("notice_period"):
            qa_lines.append(f"  • Notice Period: {qa_memory['notice_period']}")
        if qa_memory.get("work_authorization"):
            qa_lines.append(f"  • Authorized to work in target country: {qa_memory['work_authorization']}")
        if qa_memory.get("requires_sponsorship"):
            qa_lines.append(f"  • Requires visa sponsorship: {qa_memory['requires_sponsorship']}")
        if qa_memory.get("preferred_work_mode"):
            qa_lines.append(f"  • Preferred Work Mode: {qa_memory['preferred_work_mode']}")
        if qa_memory.get("custom_answers"):
            for k, v in qa_memory["custom_answers"].items():
                qa_lines.append(f"  • {k}: {v}")
        qa_block = "\n".join(qa_lines) if qa_lines else "  (No pre-filled answers)"

        # --- Skills (full list) ---
        all_skills = profile.get("skills", [])
        skills_str = ", ".join(all_skills[:25]) if isinstance(all_skills, list) else str(all_skills)

        # Build the task description for the browser agent
        task = f"""Navigate to {apply_url} and fill out the job application form.

=== CANDIDATE PERSONAL INFORMATION ===
- Full Name: {profile.get('name', '')}
- Email Address: {profile.get('email', '')}
- Phone Number: {profile.get('phone', '')}
- Location (City, Country): {profile.get('location', '')}
- Present Address: {profile.get('present_address', '')}
- Permanent Address: {profile.get('permanent_address', '')}
- Languages Known: {', '.join(profile.get('languages', [])) if isinstance(profile.get('languages'), list) else profile.get('languages', '')}
- LinkedIn URL: {profile.get('linkedin', '')}
- GitHub URL: {profile.get('github', '')}
- Portfolio / Website: {profile.get('portfolio', '')}
- Professional Summary: {profile.get('summary', '')}
- Relevant Experience: {profile.get('relevant_experience', '')}

=== TECHNICAL SKILLS ===
{skills_str}

=== EDUCATION HISTORY ===
{edu_block}

=== WORK EXPERIENCE ===
{exp_block}

=== APPLICATION Q&A ANSWERS (use these for questionnaire fields) ===
{qa_block}

CRITICAL TOKEN SAVING & SPEED RULE:
Keep your thinking extremely brief and short (1 concise sentence max). Do NOT write long explanations or reasoning. Execute actions directly to minimize token usage and complete the task fast!

=== FORM FILLING RULES ===

BASIC RULES:
1. Fill in all required fields with the candidate information above.
2. Use the Q&A answers for dropdown/select/radio/input questions about salary, CTC, notice period, work authorization, etc.
3. Do NOT fill in Current CTC or Expected CTC unless the application form explicitly asks.
4. If a generic "salary" is asked, prioritize expected salary / expected CTC.
5. For education and work experience fields, use the detailed history provided above.
6. If there is a resume upload field, call the tool `Upload candidate resume file (PDF/CV) to application form input`.
7. After filling, click the Submit/Apply button.
8. Report the final status: SUCCESS or the reason for stopping.

DROPDOWN / SELECT FIELD RULES:
- For native <select> elements: Use the built-in `dropdown_options` action to see available options, then `select_dropdown` to pick the best match.
- For custom dropdowns (React Select, Material UI, etc.): Click the dropdown to open it, then click the matching option text.
- For combobox/autocomplete fields: Type the value slowly (50ms delay per character), wait 500ms for suggestions to appear, then click the matching suggestion.
- ALWAYS use the `dropdown_options` action first to see what options are available before trying to select.
- If an option says "Other" and the form has a text field next to it, select "Other" and type the specific value.
- For "Years of Experience" dropdowns, pick the option that matches the candidate's total experience.
- For "Salary" / "Expected CTC" dropdowns, use the Q&A answers provided above.

DATE / CALENDAR FIELD RULES:
- For <input type="date"> fields: Type the date directly in MM/DD/YYYY or YYYY-MM-DD format (check the placeholder for the expected format).
- For datepicker calendar widgets: Click the input to open the calendar, then navigate to the correct month/year and click the day.
- For education dates: Use the start/end dates from the education history above.
- For work experience dates: Use the start/end dates from the work experience above.
- If a date field has a calendar popup, try clicking the input first, then type the date directly — most modern datepickers accept typed input.
- Format dates as MM/DD/YYYY unless the field clearly shows a different format.

RADIO BUTTON / CHECKBOX RULES:
- For "Yes/No" questions about work authorization, visa sponsorship, etc., use the Work Authorization Rule below.
- For gender/ethnicity questions, these are usually optional — skip unless required.
- For "How did you hear about us?" dropdowns, select "LinkedIn" or "Job Board" if available.

WORK AUTHORIZATION RULE:
- If the job is located inside India (the candidate's home country), auto-fill work authorization as "Yes" (authorized, no sponsorship needed).
- If the job is remote or outside India: if they ask about authorization to work in that country, answer based on the candidate's profile (usually "Requires sponsorship" for foreign countries).

ERROR DETECTION — STOP AND REPORT:
4. If you encounter a login page, STOP and report "LOGIN_REQUIRED".
5. If you encounter a CAPTCHA, STOP and report "CAPTCHA_DETECTED".
6. If you see an OTP/MFA prompt, STOP and report "MFA_REQUIRED".
7. If the form is too complex to fill automatically, STOP and report "TOO_COMPLEX"."""


        from vellum.api.ws import manager as ws_manager

        def _clean_action_text(output_obj: Any) -> str:
            if not output_obj:
                return "Executing browser action..."
            raw = str(output_obj)
            import re
            goal_match = re.search(r"next_goal=['\"]([^'\"]+)['\"]", raw)
            thinking_match = re.search(r"thinking=['\"]([^'\"]+)['\"]", raw)
            if goal_match:
                return f"Goal: {goal_match.group(1)}"
            elif thinking_match:
                t = thinking_match.group(1)
                return f"Thinking: {t[:120]}..." if len(t) > 120 else f"Thinking: {t}"
            return raw[:150]

        async def browser_step_callback(state, model_output, step_num):
            url = getattr(state, "url", "")
            action = _clean_action_text(model_output)
            event_data = {
                "agent": "browser_agent",
                "event_type": "browser_step",
                "job_id": job_id,
                "message": f"Browser step {step_num}: {action[:100]}",
                "data": {
                    "step": step_num,
                    "url": url,
                    "action": action,
                    "company": job.get("company", ""),
                    "role": job.get("role", "Software Engineer")
                }
            }
            await ws_manager.broadcast(event_data)


        agent_kwargs = {
            "task": task,
            "llm": llm,
            "controller": controller,
            "register_new_step_callback": browser_step_callback,
            "use_vision": True,
            "available_file_paths": [str(pdf_path.resolve())] if pdf_path else [],
        }
        if BrowserProfile is not None:
            agent_kwargs["browser_profile"] = _build_stealth_profile(settings)
        agent = Agent(**agent_kwargs)

        # Takeover gate. While cleared, the URL streamer pauses
        # broadcasting (the user is manually controlling the real Chrome window).
        # Set by default (broadcasting active); cleared on user "take over",
        # re-set on "resume".
        _takeover_gate = asyncio.Event()
        _takeover_gate.set()
        register_takeover_gate(job_id, _takeover_gate)

        _active_sessions.append(agent)

        async def url_status_streamer(agent_instance):
            """Lightweight streamer: broadcasts current URL + page title only.

            No screenshots. The real browser window stays visible on the
            user's desktop; the UI shows the live URL + activity feed and
            the user clicks to take over the actual window when needed.
            """
            await asyncio.sleep(3.0)
            while True:
                try:
                    session = getattr(agent_instance, "browser_session", None)
                    if session:
                        try:
                            url = await session.get_current_page_url()
                        except Exception:
                            url = ""
                        try:
                            title = await session.get_current_page_title()
                        except Exception:
                            title = ""
                        event_data = {
                            "agent": "browser_agent",
                            "event_type": "browser_stream_frame",
                            "job_id": job_id,
                            "data": {
                                "url": url,
                                "title": title,
                                "cdp_url": getattr(session, "cdp_url", "") or "",
                            }
                        }
                        await ws_manager.broadcast(event_data)
                except asyncio.CancelledError:
                    break
                except Exception:
                    pass

                # Pause here if the user has taken over the browser window.
                await _takeover_gate.wait()
                await asyncio.sleep(1.0)

        streamer_task = asyncio.create_task(url_status_streamer(agent))
        try:
            history = await asyncio.wait_for(agent.run(), timeout=180)
            final_result = history.final_result() if hasattr(history, 'final_result') else str(history)
        except asyncio.TimeoutError:
            final_result = "TIMEOUT"
        finally:
            streamer_task.cancel()
            try:
                await streamer_task
            except asyncio.CancelledError:
                pass
            if agent in _active_sessions:
                _active_sessions.remove(agent)
            _takeover_gates.pop(job_id, None)

        # --- Analyse result for HITL needs ---
        result_text = str(final_result).upper()

        if "LOGIN_REQUIRED" in result_text or "LOGIN" in result_text:
            hitl_type = HITLType.LOGIN
        elif "CAPTCHA" in result_text:
            hitl_type = HITLType.CAPTCHA
        elif "MFA" in result_text or "OTP" in result_text:
            hitl_type = HITLType.MFA
        elif "TOO_COMPLEX" in result_text or "TIMEOUT" in result_text:
            hitl_type = HITLType.TOO_COMPLEX
        elif "SUCCESS" in result_text:
            hitl_type = None
        else:
            hitl_type = HITLType.MANUAL_FORM

        if hitl_type is None:
            # Success!
            await db.update_job(job_id, status="applied")
            events.append(AgentEvent(
                agent="browser_agent",
                event_type="complete",
                job_id=job_id,
                message="Application submitted successfully!",
            ).model_dump(mode="json"))
            return {
                "browser_result": {"status": "applied"},
                "events": events,
                "errors": errors,
            }
        else:
            # HITL needed — save session as intervention card (non-blocking)
            await db.update_job(job_id, status="needs_attention")
            save_paused_session(job_id, reason=hitl_type.value, url=apply_url)

            # Create intervention session in DB
            db_id = None
            try:
                db_id = await db.create_intervention_session(
                    job_id=job_id,
                    hitl_type=hitl_type.value,
                    url=apply_url,
                    company=job.get("company", ""),
                    role=job.get("role", ""),
                )
            except Exception as db_exc:
                log.warning("failed_to_create_db_intervention_session", error=str(db_exc))

            # Capture screenshot of current browser state
            screenshot_path = None
            try:
                screenshot_dir = Path("./data/screenshots")
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                screenshot_path = str(screenshot_dir / f"{job_id}.png")
                # Try to get screenshot from agent's browser session
                if hasattr(agent, 'browser_session') and agent.browser_session:
                    page = await agent.browser_session.get_current_page()
                    if page and not page.is_closed():
                        await page.screenshot(path=screenshot_path, full_page=False)
                elif _active_browser_page and not _active_browser_page.is_closed():
                    await _active_browser_page.screenshot(path=screenshot_path, full_page=False)
                else:
                    screenshot_path = None
            except Exception as ss_exc:
                log.warning("screenshot_capture_failed", error=str(ss_exc))
                screenshot_path = None

            hitl_message = {
                HITLType.LOGIN: "Login required — please sign in manually, then click Continue.",
                HITLType.CAPTCHA: "CAPTCHA detected — please solve it, then click Continue.",
                HITLType.MFA: "MFA/OTP required — please complete verification, then click Continue.",
                HITLType.MANUAL_FORM: "Complex form detected — please fill remaining fields manually.",
                HITLType.TOO_COMPLEX: "Application too complex for automation. Please apply manually.",
            }.get(hitl_type, "Manual intervention needed.")

            # Broadcast intervention event to frontend (shows as card in Intervention tab)
            await ws_manager.broadcast({
                "agent": "browser_agent",
                "event_type": "intervention_needed",
                "job_id": job_id,
                "message": hitl_message,
                "data": {
                    "type": hitl_type.value,
                    "url": apply_url,
                    "company": job.get("company", ""),
                    "role": job.get("role", ""),
                    "job_id": job_id,
                    "screenshot": screenshot_path,
                    "db_id": db_id,
                },
            })

            events.append(AgentEvent(
                agent="browser_agent",
                event_type="hitl_request",
                job_id=job_id,
                message=hitl_message,
                data={"type": hitl_type.value, "url": apply_url},
            ).model_dump(mode="json"))

            return {
                "browser_result": {"status": "needs_attention", "reason": hitl_type.value},
                "events": events,
                "errors": errors,
            }

    except ImportError as exc:
        error_msg = f"browser-use not available: {exc}. Install with: pip install browser-use"
        log.error("browser_import_error", error=str(exc))
        errors.append(error_msg)
        await db.update_job(job_id, status="failed")
        events.append(AgentEvent(
            agent="browser_agent",
            event_type="error",
            job_id=job_id,
            message=error_msg,
        ).model_dump(mode="json"))
        return {"browser_result": {"status": "error"}, "events": events, "errors": errors}

    except Exception as exc:
        log.error("browser_agent_error", job_id=job_id, error=str(exc))
        errors.append(str(exc))
        await db.update_job(job_id, status="failed")
        events.append(AgentEvent(
            agent="browser_agent",
            event_type="error",
            job_id=job_id,
            message=f"Browser error: {str(exc)[:200]}",
        ).model_dump(mode="json"))
        return {"browser_result": {"status": "error"}, "events": events, "errors": errors}
