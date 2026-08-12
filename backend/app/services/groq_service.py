import asyncio
from typing import Optional

from groq import AsyncGroq

from app.core.config import settings


# ============================================================
# Groq client
# ============================================================

client = AsyncGroq(
    api_key=settings.groq_api_key
)


# ============================================================
# Model configuration
# ============================================================

MODEL_NAME = "llama-3.1-8b-instant"

REQUEST_TIMEOUT = 30

MAX_RETRIES = 3

INITIAL_RETRY_DELAY = 1.0


# ============================================================
# Generate completion
# ============================================================

async def generate_completion(
    system_prompt: str,
    user_prompt: str
) -> str:

    last_error: Optional[Exception] = None

    for attempt in range(MAX_RETRIES):

        try:

            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=MODEL_NAME,
                    temperature=0,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ]
                ),
                timeout=REQUEST_TIMEOUT
            )

            content = response.choices[0].message.content

            if not content:
                raise RuntimeError(
                    "Groq returned an empty response."
                )

            return content.strip()

        except asyncio.TimeoutError as exc:

            last_error = TimeoutError(
                "Groq request timed out."
            )

        except Exception as exc:

            last_error = exc

            error_text = str(exc).lower()

            retryable = (
                "429" in error_text
                or "rate limit" in error_text
                or "timeout" in error_text
                or "timed out" in error_text
                or "connection" in error_text
                or "temporarily unavailable" in error_text
                or "503" in error_text
                or "502" in error_text
                or "504" in error_text
            )

            if not retryable:
                raise

        # ----------------------------------------------------
        # Retry handling
        # ----------------------------------------------------

        if attempt < MAX_RETRIES - 1:

            delay = INITIAL_RETRY_DELAY * (2 ** attempt)

            await asyncio.sleep(delay)

    # ========================================================
    # All attempts failed
    # ========================================================

    raise RuntimeError(
        f"Groq completion failed after "
        f"{MAX_RETRIES} attempts: {last_error}"
    )