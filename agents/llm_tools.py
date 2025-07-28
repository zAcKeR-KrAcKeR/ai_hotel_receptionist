import os
import json
import logging
from openai import OpenAI
from langchain.tools import tool

logger = logging.getLogger(__name__)

class LLMIntentAgent:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("API KEY not set in environment variables")
        self.client = OpenAI(api_key=api_key)  # no proxies argument here
        self.model = "gpt-4o-mini"

    # keep analyze_intent method as above with docstring

    @tool("analyze_intent")
    def analyze_intent(self, user_text: str) -> dict:
        """Analyze a hotel guest utterance and return intent and entities as JSON."""
        prompt = (
            "Analyze this hotel guest utterance. Extract bookings, room type, food items, and quantities as JSON.\n"
            "Input: "
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt + user_text}],
                temperature=0.3,
                max_tokens=400,
            )
            text = response.choices[0].message.content
            data = json.loads(text)
            logger.info(f"Intent extraction result: {data}")
            return data
        except Exception as e:
            logger.error(f"Intent extraction error: {e}")
            return {"intent": "unknown", "entities": {}}

llm_tool = LLMIntentAgent()
