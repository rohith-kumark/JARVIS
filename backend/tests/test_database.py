"""Tests for database layer and ORM models."""

from backend.app.memory.conversation_manager import conversation_manager
from backend.app.memory.memory_manager import memory_manager
from backend.app.tools.manager import tool_manager


def test_conversation_and_message_lifecycle(db_session):
    # Create conversation
    conv = conversation_manager.create_conversation(db_session, title="Test Chat")
    assert conv.id is not None
    assert conv.title == "Test Chat"

    # Add messages
    m1 = conversation_manager.add_message(db_session, conv.id, "user", "Hello JARVIS")
    m2 = conversation_manager.add_message(db_session, conv.id, "assistant", "Greetings, Sir.")

    messages = conversation_manager.get_messages(db_session, conv.id)
    assert len(messages) == 2
    assert messages[0].content == "Hello JARVIS"
    assert messages[1].content == "Greetings, Sir."

    # Delete conversation and ensure cascade
    conversation_manager.delete_conversation(db_session, conv.id)
    assert len(conversation_manager.list_conversations(db_session)) == 0


def test_memory_and_preferences(db_session):
    conv = conversation_manager.create_conversation(db_session)

    # Set memories
    memory_manager.set_memory(db_session, key="user_name", value="Tony Stark", conversation_id=conv.id)
    memory_manager.set_preference(db_session, key="theme", value="dark_cyan")

    memories = memory_manager.get_memories(db_session, conversation_id=conv.id)
    assert len(memories) >= 1
    assert memories[0].key == "user_name"
    assert memories[0].value == "Tony Stark"

    prefs = memory_manager.get_preferences(db_session)
    assert prefs["theme"] == "dark_cyan"

    prompt_context = memory_manager.build_context_prompt(db_session, conversation_id=conv.id)
    assert "Tony Stark" in prompt_context
    assert "dark_cyan" in prompt_context


def test_tool_execution_tracking(db_session):
    conv = conversation_manager.create_conversation(db_session)

    info = tool_manager.execute_tool(
        tool_name="calculator",
        arguments={"expression": "100 + 200"},
        conversation_id=conv.id,
        db=db_session,
    )

    assert info.status == "success"
    assert info.result["result"] == 300
    assert len(conv.tool_executions) == 1
    assert conv.tool_executions[0].tool_name == "calculator"
