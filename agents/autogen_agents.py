from autogen import AssistantAgent, GroupChat, GroupChatManager

from agents.llm_tools import llm_tool
from agents.stt_tool import stt_tool
from agents.tts_tool import tts_tool

from agents.db_tools import (
    get_food_menu_and_voice,
    process_booking_tool,
    process_food_order_tool,
)

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

# Front Desk/Greeter Agent: redirects, clarifies, summarizes
front_agent = AssistantAgent(
    "front_desk",
    system_message="Greet guests, clarify missing information, and delegate booking or food queries to the right agent."
)

agents = [front_agent, booking_agent, food_agent]

groupchat = GroupChat(agents=agents, messages=[], max_round=6)
manager = GroupChatManager(groupchat, name="manager")
