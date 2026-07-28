"""
Vellum OS — Browser Execution Agent (Agent B)

Uses browser-use with ChatLiteLLM for form filling.
Robust HITL state machine for login, CAPTCHA, MFA, complex forms.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from vellum.config.logging import get_logger
from vellum.config import database as db
from vellum.config.settings import get_settings
from vellum.models import AgentEvent, HITLType

log = get_logger("browser_agent")


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
# Browser agent runner
# ---------------------------------------------------------------------------

_active_sessions: list[tuple[asyncio.AbstractEventLoop, Any]] = []


async def stop_all_active_browsers():
    """Halt any active browser-use Agent sessions by closing their browsers."""
    log.info("stopping_all_active_browsers", count=len(_active_sessions))
    for loop, agent in list(_active_sessions):
        try:
            if hasattr(agent, "browser") and agent.browser:
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

    # Save tailored PDF to temp file if available
    pdf_path = None
    if tailored_pdf:
        screenshots_dir = settings.screenshots_full_path / job_id
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = screenshots_dir / "tailored_resume.pdf"
        pdf_path.write_bytes(tailored_pdf)

    try:
        # --- Initialize browser-use Agent with our LLM ---
        from browser_use import Agent
        from browser_use.llm.litellm import ChatLiteLLM
        try:
            from browser_use import BrowserProfile
        except ImportError:
            BrowserProfile = None

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
2. If there is a resume upload field, upload the file at: {pdf_path or 'N/A'}. 
   CRITICAL FILE UPLOAD RULE: When uploading a resume, do NOT click the decorative/visible upload button directly. Instead, search for the hidden `<input type="file">` element (which has type="file") and perform the file upload action on that specific input element directly to avoid the Playwright 'Node is not a file input element' error.
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
            screenshot = getattr(state, "screenshot", None)
            action = _clean_action_text(model_output)
            
            if isinstance(screenshot, bytes):
                import base64
                screenshot = base64.b64encode(screenshot).decode("ascii")
            event_data = {
                "agent": "browser_agent",
                "event_type": "browser_step",
                "job_id": job_id,
                "message": f"Browser step {step_num}: {action[:100]}",
                "data": {
                    "step": step_num,
                    "url": url,
                    "screenshot": screenshot,
                    "action": action,
                    "company": job.get("company", ""),
                    "role": job.get("role", "Software Engineer")
                }
            }
            await ws_manager.broadcast(event_data)


        agent_kwargs = {
            "task": task,
            "llm": llm,
            "register_new_step_callback": browser_step_callback,
            "use_vision": True,
            "available_file_paths": [str(pdf_path)] if pdf_path else [],
        }
        if BrowserProfile is not None:
            agent_kwargs["browser_profile"] = BrowserProfile(
                headless=settings.browser_use_headless
            )
        agent = Agent(**agent_kwargs)

        # Run browser agent in a dedicated thread with ProactorEventLoop.
        # On Windows, the main uvicorn event loop may be a SelectorEventLoop
        # (e.g. from watchfiles reload subprocess), which cannot create
        # subprocesses. A dedicated thread with ProactorEventLoop fixes this.
        def _run_agent_in_proactor_loop():
            import concurrent.futures
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            _active_sessions.append((loop, agent))

            async def screenshot_streamer(agent_instance):
                import base64
                # Give browser a few seconds to boot up
                await asyncio.sleep(4.0)
                while True:
                    try:
                        session = getattr(agent_instance, "browser_session", None)
                        if session:
                            page = await session.get_current_page()
                            if page and not page.is_closed():
                                screenshot_bytes = await page.screenshot(type="jpeg", quality=50)
                                screenshot_b64 = base64.b64encode(screenshot_bytes).decode("ascii")
                                url = page.url
                                
                                event_data = {
                                    "agent": "browser_agent",
                                    "event_type": "browser_stream_frame",
                                    "job_id": job_id,
                                    "data": {
                                        "url": url,
                                        "screenshot": screenshot_b64
                                    }
                                }
                                await ws_manager.broadcast(event_data)
                    except asyncio.CancelledError:
                        break
                    except Exception:
                        pass
                    await asyncio.sleep(0.5)

            streamer_task = loop.create_task(screenshot_streamer(agent))
            try:
                return loop.run_until_complete(
                    asyncio.wait_for(agent.run(), timeout=120)
                )
            finally:
                streamer_task.cancel()
                if (loop, agent) in _active_sessions:
                    _active_sessions.remove((loop, agent))
                loop.close()

        loop = asyncio.get_running_loop()
        try:
            history = await loop.run_in_executor(
                None, _run_agent_in_proactor_loop
            )
            final_result = history.final_result() if hasattr(history, 'final_result') else str(history)
        except asyncio.TimeoutError:
            final_result = "TIMEOUT"

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
