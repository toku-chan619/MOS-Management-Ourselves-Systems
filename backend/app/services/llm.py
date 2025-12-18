from app.core.config import settings

async def call_llm_json(system_prompt: str, user_text: str) -> dict:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")

    from openai import AsyncOpenAI
    import json

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    resp = await client.responses.create(
        model=settings.LLM_MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    return json.loads(resp.output_text)
