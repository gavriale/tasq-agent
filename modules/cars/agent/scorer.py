"""Claude scorer for car listings — assesses deal quality and flags red flags."""

import logging

from anthropic import Anthropic

from core.config import ANTHROPIC_API_KEY, MAX_DAILY_TOKENS
from core.db.database import get_tokens_used_today, increment_token_usage

logger = logging.getLogger(__name__)

client = Anthropic(api_key=ANTHROPIC_API_KEY)

_SYSTEM = """You are a used car advisor in Israel. Given a car listing, assess the deal briefly.
Respond in this exact format (no extra text):
SCORE: <1-10>
VERDICT: <one line summary>
NOTES:
- <point 1>
- <point 2>
- <point 3 if needed>

Scoring guide:
9-10: Excellent deal, below market, low km, low hand
7-8: Good deal, fair price, reasonable km
5-6: Average, nothing special but not bad
3-4: Overpriced or has concerns
1-2: Red flags, avoid"""

_PROMPT = """Car listing:
- Make/Model: {manufacturer} {model} ({sub_model})
- Year: {year}
- Price: {price:,} NIS
- KM: {km:,}
- Color: {color}
- Hand (owners): {hand}
- Engine: {engine_type}
- Area: {area}
- URL: {url}

Assess this listing."""


def score_car(car) -> dict | None:
    """Score a car listing with Claude. Returns dict with score/verdict/notes or None."""
    if get_tokens_used_today() >= MAX_DAILY_TOKENS:
        logger.warning("[Cars] Daily token cap reached, skipping score")
        return None

    prompt = _PROMPT.format(
        manufacturer=car.manufacturer,
        model=car.model,
        sub_model=car.sub_model,
        year=car.year,
        price=car.price,
        km=car.km,
        color=car.color,
        hand=car.hand,
        engine_type=car.engine_type,
        area=car.area,
        url=car.url,
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        usage = response.usage.input_tokens + response.usage.output_tokens
        increment_token_usage(usage)

        text = response.content[0].text.strip()
        return _parse_response(text)
    except Exception as e:
        logger.error("[Cars] Scoring failed: %s", e)
        return None


def _parse_response(text: str) -> dict:
    lines = text.splitlines()
    score = 0
    verdict = ""
    notes = []

    for line in lines:
        line = line.strip()
        if line.startswith("SCORE:"):
            try:
                score = int(line.split(":", 1)[1].strip())
            except ValueError:
                score = 0
        elif line.startswith("VERDICT:"):
            verdict = line.split(":", 1)[1].strip()
        elif line.startswith("- "):
            notes.append(line[2:])

    return {"score": score, "verdict": verdict, "notes": notes}
