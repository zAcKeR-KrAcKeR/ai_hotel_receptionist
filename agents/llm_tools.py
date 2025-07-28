import os
import json
import logging
from openai import OpenAI
from langchain.tools import tool

logger = logging.getLogger(__name__)

class LLMIntentAgent:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"), 
            base_url=os.getenv("DEEPSEEK_BASE_URL","")
        )
        self.model = "deepseek-chat"

    @tool("analyze_intent")
    def analyze_intent(self, user_text: str) -> dict:
        prompt = (
            "Analyze this hotel guest utterance. "
            "Extract as much as possible: room type, guest name, check-in/check-out, food_items, quantity. "
            "Respond as JSON format: {'intent':..., 'entities': {...}}\n"
        )
        try:
            r = self.client.chat.completions.create(
                model=self.model, messages=[
                    {"role": "user", "content": prompt + f"Utterance: {user_text}"}
                ],
                max_tokens=400, temperature=0.3
            )
            result = json.loads(r.choices[0].message.content)
            logger.info(f"LLM intent extraction result: {result}")
            return result
        except Exception as e:
            logger.error(f"LLM intent extraction error: {e}")
            return {"intent": "other", "entities": {}}

llm_tool = LLMIntentAgent()

