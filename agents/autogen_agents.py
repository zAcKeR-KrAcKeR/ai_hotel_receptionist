import os
from autogen import AssistantAgent, GroupChat, GroupChatManager
from agents.llm_tools import llm_tool
from agents.stt_tool import stt_tool
from agents.tts_tool import tts_tool  # LangChain tool singleton
from agents.db_tools import get_food_menu_and_voice, process_booking_tool, process_food_order

PUBLIC_WEBHOOK_MODE = os.getenv("PUBLIC_WEBHOOK_MODE", "").lower() in ("true", "1", "yes")

booking_agent = AssistantAgent("booking_agent", system_message="Booking and enquiries.")
booking_agent.register_for_execution("process_booking_tool", process_booking_tool)

food_agent = AssistantAgent("food_agent", system_message="Food related.")
food_agent.register_for_execution("get_food_menu_and_voice", get_food_menu_and_voice)
food_agent.register_for_execution("process_food_order", process_food_order)

front_agent = AssistantAgent("front_agent", system_message="Front desk, greeter.")
if not PUBLIC_WEBHOOK_MODE:
    front_agent.register_for_execution("synthesize_speech", tts_tool.synthesize_speech)
    booking_agent.register_for_execution("synthesize_speech", tts_tool.synthesize_speech)
    food_agent.register_for_execution("synthesize_speech", tts_tool.synthesize_speech)
else:
    def tts_stub(text):
        return ""
    front_agent.register_for_execution("synthesize_speech", tts_stub)
    booking_agent.register_for_execution("synthesize_speech", tts_stub)
    food_agent.register_for_execution("synthesize_speech", tts_stub)

agents = [front_agent, booking_agent, food_agent]
groupchat = GroupChat(agents=agents, messages=[], max_round=6)
manager = GroupChatManager(groupchat, name="manager")
