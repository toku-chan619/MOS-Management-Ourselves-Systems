from app.core.config import settings

async def call_llm_json(system_prompt: str, user_text: str) -> dict:
    """
    返り値は「dict(JSON)」前提。
    OpenAI以外でもここを差し替えればOK。
    """
    from openai import AsyncOpenAI
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
    return resp.output_text and __import__("json").loads(resp.output_text)
