import os, json
from openai import OpenAI
from langchain.tools import tool
class LLMIntentAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=os.getenv("DEEPSEEK_BASE_URL",""))
        self.model = "deepseek-chat"
    @tool("analyze_intent")
    def analyze_intent(self, user_text: str) -> dict:
        prompt = (
            "Analyze this hotel guest utterance. "
            "Extract as much as possible: room type, guest name, check-in/check-out, food_items, quantity. "
            "Respond as JSON format: {'intent':..., 'entities': {...}}"
        )
        try:
            r = self.client.chat.completions.create(
                model=self.model, messages=[
                    {"role":"user","content":prompt+f"\nUtterance: {user_text}"}
                ], max_tokens=400, temperature=0.3
            )
            return json.loads(r.choices[0].message.content)
        except Exception: return {"intent":"other", "entities":{}}
llm_tool = LLMIntentAgent()

