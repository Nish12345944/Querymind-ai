import asyncio

from app.services.groq_service import generate_completion


async def main():
    result = await generate_completion(
        system_prompt="You are a helpful assistant.",
        user_prompt="Reply with exactly: OK",
    )

    print(result)


asyncio.run(main())