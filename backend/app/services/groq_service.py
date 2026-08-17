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

MODEL_NAME = "llama-3.3-70b-versatile"

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
    """
    Generate a deterministic completion from Groq.

    The function includes:
    - timeout protection
    - retry handling
    - exponential backoff
    - empty-response protection
    """

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

            if not response.choices:

                raise RuntimeError(
                    "Groq returned no completion choices."
                )

            content = (
                response
                .choices[0]
                .message
                .content
            )

            if not content:

                raise RuntimeError(
                    "Groq returned an empty response."
                )

            return content.strip()

        except asyncio.TimeoutError:

            last_error = TimeoutError(
                "Groq request timed out."
            )

        except Exception as exc:

            last_error = exc

            error_text = str(exc).lower()

            retryable = any(
                marker in error_text
                for marker in (
                    "429",
                    "rate limit",
                    "timeout",
                    "timed out",
                    "connection",
                    "temporarily unavailable",
                    "503",
                    "502",
                    "504",
                )
            )

            # ------------------------------------------------
            # Do not retry permanent errors
            # ------------------------------------------------

            if not retryable:
                raise

        # ----------------------------------------------------
        # Exponential backoff
        # ----------------------------------------------------

        if attempt < MAX_RETRIES - 1:

            delay = (
                INITIAL_RETRY_DELAY
                * (2 ** attempt)
            )

            await asyncio.sleep(delay)

    # ========================================================
    # All attempts failed
    # ========================================================

    raise RuntimeError(
        "Groq completion failed after "
        f"{MAX_RETRIES} attempts: {last_error}"
    )