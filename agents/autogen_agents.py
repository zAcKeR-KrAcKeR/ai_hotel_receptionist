import os
from autogen import AssistantAgent, GroupChat, GroupChatManager

from agents.llm_tools import llm_tool
from agents.stt_tool import stt_tool

# Only import the LangChain tool for agent context
from agents.tts_tool import tts_tool

from agents.db_tools import (
    get_food_menu_and_voice,
    process_booking_tool,
    process_food_order_tool,
)

# --------------------------------------------------------------------
# Context flag: set in ENV when running webhook/server mode
# e.g. Render startup ENV PUBLIC_WEBHOOK_MODE=true
# or detect from another runtime signal
# --------------------------------------------------------------------
PUBLIC_WEBHOOK_MODE = os.getenv("PUBLIC_WEBHOOK_MODE", "").lower() in ("1", "true", "yes")

# ----------------------------- Agents ------------------------------

# Booking Agent
booking_agent = AssistantAgent(
    "booking_agent",
    system_message="Handle all room booking and room inquiry tasks for users."
)
booking_agent.register_for_execution("process_booking_tool", process_booking_tool)

# Food Agent
food_agent = AssistantAgent(
    "food_agent",
    system_message="Handle food menu explanations and food order booking. Offer the menu if the user is vague."
)
food_agent.register_for_execution("get_food_menu_and_voice", get_food_menu_and_voice)
food_agent.register_for_execution("process_food_order_tool", process_food_order_tool)

# Front Desk / Greeter Agent
front_agent = AssistantAgent(
    "front_desk",
    system_message="Greet guests, clarify missing information, and delegate booking or food queries to the right agent."
)

# --------------------------------------------------------------------
# SAFE TTS REGISTRATION:
# Only register the TTS tool for internal agent use if not in webhook mode
# --------------------------------------------------------------------
if not PUBLIC_WEBHOOK_MODE:
    # This allows agents to use the TTS tool in internal/multi-agent runs
    front_agent.register_for_execution("synthesize_speech", tts_tool.synthesize_speech)
    booking_agent.register_for_execution("synthesize_speech", tts_tool.synthesize_speech)
    food_agent.register_for_execution("synthesize_speech", tts_tool.synthesize_speech)
else:
    # In webhook mode, register a stub/no-op to avoid schema validation error
    def tts_stub(text: str) -> str:
        return ""  # no synthesis in webhook context
    front_agent.register_for_execution("synthesize_speech", tts_stub)
    booking_agent.register_for_execution("synthesize_speech", tts_stub)
    food_agent.register_for_execution("synthesize_speech", tts_stub)

# --------------------------- Group Chat ----------------------------

agents = [front_agent, booking_agent, food_agent]

groupchat = GroupChat(agents=agents, messages=[], max_round=6)
manager = GroupChatManager(groupchat, name="manager")
