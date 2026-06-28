import json
import logging
import random
from typing import Any

from groq import Groq
from pydantic import BaseModel, field_validator

from config import settings

logger = logging.getLogger(__name__)

# ── Pydantic schema for generated question ─────────────────────────────────

class GeneratedQuestion(BaseModel):
    text: str
    option_a: str
    option_b: str
    emoji_a: str
    emoji_b: str

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text is empty")
        if len(v) > 500:
            raise ValueError("text too long")
        return v

    @field_validator("option_a", "option_b")
    @classmethod
    def option_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("option is empty")
        if len(v) > 200:
            raise ValueError("option too long")
        return v

    @field_validator("emoji_a", "emoji_b")
    @classmethod
    def single_emoji(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("emoji is empty")
        return v


# ── 50 fallback questions (emoji + universal text, no language required) ───

FALLBACK_QUESTIONS: list[dict[str, str]] = [
    {"text": "Which do you prefer to wake up to?", "option_a": "Sunrise", "option_b": "Stay in bed", "emoji_a": "🌅", "emoji_b": "🛏️"},
    {"text": "Pizza or burger?", "option_a": "Pizza", "option_b": "Burger", "emoji_a": "🍕", "emoji_b": "🍔"},
    {"text": "Mountains or beach?", "option_a": "Mountains", "option_b": "Beach", "emoji_a": "🏔️", "emoji_b": "🏖️"},
    {"text": "Cat or dog?", "option_a": "Cat", "option_b": "Dog", "emoji_a": "🐱", "emoji_b": "🐶"},
    {"text": "Coffee or tea?", "option_a": "Coffee", "option_b": "Tea", "emoji_a": "☕", "emoji_b": "🍵"},
    {"text": "Summer or winter?", "option_a": "Summer", "option_b": "Winter", "emoji_a": "☀️", "emoji_b": "❄️"},
    {"text": "Night owl or early bird?", "option_a": "Night owl", "option_b": "Early bird", "emoji_a": "🦉", "emoji_b": "🐦"},
    {"text": "Sweet or salty?", "option_a": "Sweet", "option_b": "Salty", "emoji_a": "🍫", "emoji_b": "🧂"},
    {"text": "City or countryside?", "option_a": "City", "option_b": "Countryside", "emoji_a": "🏙️", "emoji_b": "🌾"},
    {"text": "Reading or watching?", "option_a": "Reading", "option_b": "Watching", "emoji_a": "📚", "emoji_b": "📺"},
    {"text": "Shower in morning or evening?", "option_a": "Morning", "option_b": "Evening", "emoji_a": "🌅", "emoji_b": "🌙"},
    {"text": "Phone in silence or vibrate?", "option_a": "Silence", "option_b": "Vibrate", "emoji_a": "🔕", "emoji_b": "📳"},
    {"text": "Walk or drive?", "option_a": "Walk", "option_b": "Drive", "emoji_a": "🚶", "emoji_b": "🚗"},
    {"text": "Cook at home or eat out?", "option_a": "Cook", "option_b": "Eat out", "emoji_a": "🍳", "emoji_b": "🍽️"},
    {"text": "Plan everything or go with the flow?", "option_a": "Plan", "option_b": "Improvise", "emoji_a": "📋", "emoji_b": "🎲"},
    {"text": "Introvert or extrovert?", "option_a": "Introvert", "option_b": "Extrovert", "emoji_a": "🏠", "emoji_b": "🎉"},
    {"text": "Chocolate or vanilla?", "option_a": "Chocolate", "option_b": "Vanilla", "emoji_a": "🍫", "emoji_b": "🍦"},
    {"text": "Money or time?", "option_a": "Money", "option_b": "Time", "emoji_a": "💰", "emoji_b": "⏰"},
    {"text": "Rain or sunshine?", "option_a": "Rain", "option_b": "Sunshine", "emoji_a": "🌧️", "emoji_b": "☀️"},
    {"text": "Cats videos or dog videos?", "option_a": "Cats", "option_b": "Dogs", "emoji_a": "🐱", "emoji_b": "🐕"},
    {"text": "Sci-fi or fantasy?", "option_a": "Sci-fi", "option_b": "Fantasy", "emoji_a": "🚀", "emoji_b": "🧙"},
    {"text": "Sneakers or boots?", "option_a": "Sneakers", "option_b": "Boots", "emoji_a": "👟", "emoji_b": "👢"},
    {"text": "Pancakes or waffles?", "option_a": "Pancakes", "option_b": "Waffles", "emoji_a": "🥞", "emoji_b": "🧇"},
    {"text": "Spring or autumn?", "option_a": "Spring", "option_b": "Autumn", "emoji_a": "🌸", "emoji_b": "🍂"},
    {"text": "Music or podcasts?", "option_a": "Music", "option_b": "Podcasts", "emoji_a": "🎵", "emoji_b": "🎙️"},
    {"text": "Spicy or mild food?", "option_a": "Spicy", "option_b": "Mild", "emoji_a": "🌶️", "emoji_b": "🥛"},
    {"text": "Fast internet or long battery?", "option_a": "Fast internet", "option_b": "Long battery", "emoji_a": "⚡", "emoji_b": "🔋"},
    {"text": "Sunrise hike or sunset stroll?", "option_a": "Sunrise hike", "option_b": "Sunset stroll", "emoji_a": "🏔️", "emoji_b": "🌆"},
    {"text": "Sushi or tacos?", "option_a": "Sushi", "option_b": "Tacos", "emoji_a": "🍣", "emoji_b": "🌮"},
    {"text": "Travel alone or with friends?", "option_a": "Alone", "option_b": "Friends", "emoji_a": "🧳", "emoji_b": "👫"},
    {"text": "Phone call or text message?", "option_a": "Call", "option_b": "Text", "emoji_a": "📞", "emoji_b": "💬"},
    {"text": "Watch news or avoid it?", "option_a": "Watch", "option_b": "Avoid", "emoji_a": "📰", "emoji_b": "🙈"},
    {"text": "Gym or outdoor workout?", "option_a": "Gym", "option_b": "Outdoor", "emoji_a": "🏋️", "emoji_b": "🌳"},
    {"text": "Headphones or speakers?", "option_a": "Headphones", "option_b": "Speakers", "emoji_a": "🎧", "emoji_b": "🔊"},
    {"text": "Buy new or fix old?", "option_a": "Buy new", "option_b": "Fix old", "emoji_a": "🛒", "emoji_b": "🔧"},
    {"text": "Cold shower or hot shower?", "option_a": "Cold", "option_b": "Hot", "emoji_a": "🧊", "emoji_b": "♨️"},
    {"text": "Dessert before or after meal?", "option_a": "Before", "option_b": "After", "emoji_a": "🍰", "emoji_b": "🍽️"},
    {"text": "Work from home or office?", "option_a": "Home", "option_b": "Office", "emoji_a": "🏠", "emoji_b": "🏢"},
    {"text": "Camping or hotel?", "option_a": "Camping", "option_b": "Hotel", "emoji_a": "⛺", "emoji_b": "🏨"},
    {"text": "Morning workout or evening workout?", "option_a": "Morning", "option_b": "Evening", "emoji_a": "🌄", "emoji_b": "🌆"},
    {"text": "Paper book or e-reader?", "option_a": "Paper", "option_b": "E-reader", "emoji_a": "📖", "emoji_b": "📱"},
    {"text": "Cash or card payment?", "option_a": "Cash", "option_b": "Card", "emoji_a": "💵", "emoji_b": "💳"},
    {"text": "Elevator or stairs?", "option_a": "Elevator", "option_b": "Stairs", "emoji_a": "🛗", "emoji_b": "🪜"},
    {"text": "Early Christmas prep or last minute?", "option_a": "Early", "option_b": "Last minute", "emoji_a": "🎄", "emoji_b": "⏱️"},
    {"text": "Window seat or aisle seat?", "option_a": "Window", "option_b": "Aisle", "emoji_a": "🪟", "emoji_b": "💺"},
    {"text": "Socks then shoes, or shoes then socks?", "option_a": "Socks first", "option_b": "One foot at a time", "emoji_a": "🧦", "emoji_b": "👟"},
    {"text": "Pool or ocean?", "option_a": "Pool", "option_b": "Ocean", "emoji_a": "🏊", "emoji_b": "🌊"},
    {"text": "Left side or right side of the bed?", "option_a": "Left", "option_b": "Right", "emoji_a": "⬅️", "emoji_b": "➡️"},
    {"text": "Nap or push through?", "option_a": "Nap", "option_b": "Push through", "emoji_a": "😴", "emoji_b": "💪"},
    {"text": "Buy experiences or things?", "option_a": "Experiences", "option_b": "Things", "emoji_a": "🎡", "emoji_b": "📦"},
]

_SYSTEM_PROMPT = """You are a question designer for a daily mobile game called CROWD.
Rules:
- Generate ONE binary-choice question that a global audience can relate to
- Avoid politics, religion, or anything offensive
- Topics: food, nature, habits, animals, time of day, seasons, technology, travel
- Both options must be equally appealing (no obvious correct answer)
- Keep text SHORT: question ≤ 80 chars, each option ≤ 30 chars
- Use a single emoji per option (real Unicode emoji)
- Response MUST be valid JSON only, no markdown, no extra text

JSON format:
{
  "text": "question text here",
  "option_a": "First option",
  "option_b": "Second option",
  "emoji_a": "🎯",
  "emoji_b": "🎲"
}"""

_USER_PROMPT_TEMPLATE = "Generate a fresh daily question. Topic hint: {topic}. Make it different from common questions."

_TOPICS = [
    "food and drinks", "nature and weather", "daily habits", "animals",
    "technology gadgets", "travel and places", "seasons", "social behavior",
    "sleep and rest", "fitness and health", "entertainment", "home life",
]


def _fallback_question() -> GeneratedQuestion:
    raw = random.choice(FALLBACK_QUESTIONS)
    return GeneratedQuestion(**raw)


_THEME_KEYWORDS: dict[str, list[str]] = {
    "food": ["pizza", "burger", "sushi", "tacos", "pancakes", "waffles", "chocolate", "vanilla", "spicy", "sweet", "cook", "eat"],
    "nature": ["mountains", "beach", "rain", "sunshine", "summer", "winter", "spring", "autumn", "pool", "ocean"],
    "animals": ["cat", "dog", "cats", "dogs"],
    "travel": ["camping", "hotel", "travel", "window", "aisle", "city", "countryside"],
    "tech": ["internet", "battery", "headphones", "speakers", "phone", "e-reader"],
    "habits": ["morning", "evening", "shower", "workout", "gym", "sleep", "nap", "coffee", "tea"],
}

_THEME_FALLBACKS: dict[str, list[str]] = {
    "food": ["Pizza or burger?", "Sushi or tacos?", "Pancakes or waffles?", "Chocolate or vanilla?", "Spicy or mild food?", "Sweet or salty?", "Cook at home or eat out?", "Dessert before or after meal?"],
}


def _fallback_question_by_theme(theme: str) -> GeneratedQuestion:
    theme_lower = theme.lower()
    # Find matching questions by keyword
    matched = []
    for keyword_theme, keywords in _THEME_KEYWORDS.items():
        if theme_lower in keyword_theme or keyword_theme in theme_lower or any(k in theme_lower for k in keywords):
            for q in FALLBACK_QUESTIONS:
                text_lower = q["text"].lower()
                opt_lower = (q["option_a"] + " " + q["option_b"]).lower()
                if any(k in text_lower or k in opt_lower for k in keywords):
                    matched.append(q)
    if matched:
        return GeneratedQuestion(**random.choice(matched))
    return _fallback_question()


def generate_question_by_theme(theme: str) -> GeneratedQuestion:
    """Generate a question on a specific theme via Groq, falling back to hardcoded list."""
    if not getattr(settings, "groq_api_key", None):
        logger.warning("GROQ_API_KEY not set — using fallback question for theme: %s", theme)
        return _fallback_question_by_theme(theme)

    prompt = (
        f'Generate a fun "would you rather" or preference question about the theme: {theme}.\n'
        'Return JSON: {"text": "...", "option_a": "...", "option_b": "...", "emoji_a": "...", "emoji_b": "..."}\n'
        "All text in Ukrainian language."
    )
    try:
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=256,
            response_format={"type": "json_object"},
        )
        raw_content = response.choices[0].message.content
        data: dict[str, Any] = json.loads(raw_content)
        question = GeneratedQuestion(**data)
        logger.info("Groq generated themed question (%s): %s", theme, question.text)
        return question
    except Exception as exc:
        logger.error("Groq themed generation failed (%s) — using fallback", exc)
        return _fallback_question_by_theme(theme)


def generate_daily_question() -> GeneratedQuestion:
    """Generate today's question via Groq, falling back to hardcoded list."""
    if not getattr(settings, "groq_api_key", None):
        logger.warning("GROQ_API_KEY not set — using fallback question")
        return _fallback_question()

    topic = random.choice(_TOPICS)
    try:
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _USER_PROMPT_TEMPLATE.format(topic=topic)},
            ],
            temperature=0.9,
            max_tokens=256,
            response_format={"type": "json_object"},
        )
        raw_content = response.choices[0].message.content
        data: dict[str, Any] = json.loads(raw_content)
        question = GeneratedQuestion(**data)
        logger.info("Groq generated question: %s", question.text)
        return question

    except Exception as exc:
        logger.error("Groq generation failed (%s) — using fallback", exc)
        return _fallback_question()
