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
        enable_default_extensions=True,
        disable_security=False,
        captcha_solver=True,
        keep_alive=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process,AutomationControlled",
            "--disable-popup-blocking",
        ],
    )


# ---------------------------------------------------------------------------
# Browser agent runner
# ---------------------------------------------------------------------------

_active_sessions: list[tuple[asyncio.AbstractEventLoop, Any]] = []

# Registry of takeover gates keyed by job_id. Allows the API layer to pause/
# resume the URL streamer (and signal the agent to yield) when the user takes
# over the live browser window. Each value is a thread-safe asyncio.Event
# belonging to the agent thread's event loop.
_takeover_gates: dict[str, asyncio.Event] = {}


def register_takeover_gate(job_id: str, gate: asyncio.Event) -> None:
    _takeover_gates[job_id] = gate


def _set_gate_threadsafe(job_id: str, value: bool) -> None:
    """Set the takeover gate for a job from any thread."""
    gate = _takeover_gates.get(job_id)
    if gate is None:
        return
    loop = None
    for ev_loop, agent in _active_sessions:
        sess = getattr(agent, "browser_session", None)
        if sess is not None:
            loop = ev_loop
            break
    if loop is None:
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
    """Pause the active browser-use Agent (stops executing steps).

    Thread-safe: uses call_soon_threadsafe to modify the agent's asyncio.Event
    from the API thread while the agent runs on a separate ProactorEventLoop.
    """
    for loop, agent in _active_sessions:
        if hasattr(agent, "pause") and hasattr(agent, "_external_pause_event"):
            try:
                def _do_pause():
                    agent.state.paused = True
                    agent._external_pause_event.clear()
                loop.call_soon_threadsafe(_do_pause)
                log.info("agent_paused", session_id=getattr(agent, "session_id", ""))
            except Exception as exc:
                log.warning("agent_pause_failed", error=str(exc))


def _resume_active_agent() -> None:
    """Resume the active browser-use Agent (resumes executing steps).

    Thread-safe: uses call_soon_threadsafe to modify the agent's asyncio.Event
    from the API thread while the agent runs on a separate ProactorEventLoop.
    """
    for loop, agent in _active_sessions:
        if hasattr(agent, "resume") and hasattr(agent, "_external_pause_event"):
            try:
                def _do_resume():
                    agent.state.paused = False
                    agent._external_pause_event.set()
                loop.call_soon_threadsafe(_do_resume)
                log.info("agent_resumed", session_id=getattr(agent, "session_id", ""))
            except Exception as exc:
                log.warning("agent_resume_failed", error=str(exc))


def get_active_cdp_url() -> str:
    """Return the CDP websocket URL of the currently active browser, if any."""
    for _loop, agent in _active_sessions:
        sess = getattr(agent, "browser_session", None)
        if sess is not None:
            cdp = getattr(sess, "cdp_url", "") or ""
            if cdp:
                return cdp
    return ""


def get_active_browser_session() -> Any:
    """Return the active BrowserSession object, or None."""
    for _loop, agent in _active_sessions:
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
    for loop, agent in list(_active_sessions):
        try:
            if hasattr(agent, "stop"):
                agent.stop()
            if hasattr(agent, "browser_session") and agent.browser_session:
                async def _close_session():
                    try:
                        await agent.browser_session.close()
                    except Exception:
                        pass
                asyncio.run_coroutine_threadsafe(_close_session(), loop)
            elif hasattr(agent, "browser") and agent.browser:
                async def _close():
                    try:
                        await agent.browser.close()
                    except Exception:
                        pass
                asyncio.run_coroutine_threadsafe(_close(), loop)
        except Exception as exc:
            log.warning("error_triggering_browser_close", error=str(exc))
    _active_sessions.clear()


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

        # Use our LiteLLM router — forced to gemini-3.1-flash-lite per spec
        llm = ChatLiteLLM(model="gemini/gemini-3.1-flash-lite")

        # Build the task description for the browser agent
        task = f"""Navigate to {apply_url} and fill out the job application form.

Candidate Information:
- Name: {profile.get('name', '')}
- Email: {profile.get('email', '')}
- Phone: {profile.get('phone', '')}
- Location: {profile.get('location', '')}
- Present Address: {profile.get('present_address', '')}
- Permanent Address: {profile.get('permanent_address', '')}
- Languages Known: {', '.join(profile.get('languages', [])) if isinstance(profile.get('languages'), list) else profile.get('languages', '')}
- Key Skills: {', '.join(profile.get('skills', [])[:15]) if isinstance(profile.get('skills'), list) else profile.get('skills', '')}
- LinkedIn: {profile.get('linkedin', '')}
- GitHub: {profile.get('github', '')}
- Portfolio: {profile.get('portfolio', '')}
- Professional Summary: {profile.get('summary', '')}

CRITICAL TOKEN SAVING & SPEED RULE:
Keep your thinking extremely brief and short (1 concise sentence max). Do NOT write long explanations or reasoning. Execute actions directly to minimize token usage and complete the task fast!

Instructions:
1. Fill in all required fields with the candidate information above.
2. If there is a resume upload field, call the tool `Upload candidate resume file (PDF/CV) to application form input`.
3. If you encounter a login page, STOP and report "LOGIN_REQUIRED".
4. If you encounter a CAPTCHA, STOP and report "CAPTCHA_DETECTED".
5. If you see an OTP/MFA prompt, STOP and report "MFA_REQUIRED".
6. If the form is too complex to fill automatically, STOP and report "TOO_COMPLEX".
7. After filling, click the Submit/Apply button.
8. Report the final status: SUCCESS or the reason for stopping."""


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

        # Run browser agent in a dedicated thread with ProactorEventLoop.
        main_loop = asyncio.get_running_loop()

        # Cross-thread takeover gate. While cleared, the URL streamer pauses
        # broadcasting (the user is manually controlling the real Chrome window).
        # Set by default (broadcasting active); cleared on user "take over",
        # re-set on "resume".
        _takeover_gate = asyncio.Event()
        _takeover_gate.set()
        register_takeover_gate(job_id, _takeover_gate)

        def _run_agent_in_proactor_loop():
            import concurrent.futures
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            _active_sessions.append((loop, agent))

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
                            page = await session.get_current_page()
                            if page and not page.is_closed():
                                url = page.url
                                try:
                                    title = await page.title()
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
                                ws_manager.broadcast_threadsafe(event_data, main_loop)
                    except asyncio.CancelledError:
                        break
                    except Exception:
                        pass

                    # Pause here if the user has taken over the browser window.
                    await _takeover_gate.wait()
                    await asyncio.sleep(1.0)

            streamer_task = loop.create_task(url_status_streamer(agent))
            try:
                return loop.run_until_complete(
                    asyncio.wait_for(agent.run(), timeout=180)
                )
            finally:
                streamer_task.cancel()
                if (loop, agent) in _active_sessions:
                    _active_sessions.remove((loop, agent))
                loop.close()

        try:
            history = await main_loop.run_in_executor(
                None, _run_agent_in_proactor_loop
            )
            final_result = history.final_result() if hasattr(history, 'final_result') else str(history)
        except asyncio.TimeoutError:
            final_result = "TIMEOUT"
        finally:
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
            # HITL needed — use LangGraph interrupt
            await db.update_job(job_id, status="needs_attention")

            hitl_message = {
                HITLType.LOGIN: "Login required — please sign in manually, then click Resume.",
                HITLType.CAPTCHA: "CAPTCHA detected — please solve it, then click Resume.",
                HITLType.MFA: "MFA/OTP required — please complete verification, then click Resume.",
                HITLType.MANUAL_FORM: "Complex form detected — please fill remaining fields manually.",
                HITLType.TOO_COMPLEX: "Application too complex for automation. Please apply manually.",
            }.get(hitl_type, "Manual intervention needed.")

            events.append(AgentEvent(
                agent="browser_agent",
                event_type="hitl_request",
                job_id=job_id,
                message=hitl_message,
                data={"type": hitl_type.value, "url": apply_url},
            ).model_dump(mode="json"))

            # Interrupt for human input
            from langgraph.types import interrupt

            human_response = interrupt({
                "type": hitl_type.value,
                "job_id": job_id,
                "url": apply_url,
                "message": hitl_message,
            })

            # User responded — check action
            action = human_response if isinstance(human_response, str) else human_response.get("action", "skip")

            if action == "skip":
                await db.update_job(job_id, status="skipped")
                events.append(AgentEvent(
                    agent="browser_agent",
                    event_type="progress",
                    job_id=job_id,
                    message="User skipped this application",
                ).model_dump(mode="json"))
                return {
                    "browser_result": {"status": "skipped"},
                    "events": events,
                    "errors": errors,
                }
            else:
                # User completed the manual step — mark as applied
                await db.update_job(job_id, status="applied")
                events.append(AgentEvent(
                    agent="browser_agent",
                    event_type="complete",
                    job_id=job_id,
                    message="Application completed (with manual assistance)",
                ).model_dump(mode="json"))
                return {
                    "browser_result": {"status": "applied_manual"},
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
        # DO NOT swallow or catch LangGraph Interrupt exceptions
        if exc.__class__.__name__ == "Interrupt" or "Interrupt" in str(type(exc)):
            raise exc
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
