from groq import AsyncGroq

from app.core.config import settings


client = AsyncGroq(
    api_key=settings.groq_api_key
)


MODEL_NAME = "openai/gpt-oss-120b"


async def generate_completion(
    system_prompt: str,
    user_prompt: str
):

    response = await client.chat.completions.create(
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
    )

    return response.choices[0].message.content.strip()