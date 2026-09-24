import pytest
from google.genai import types
from backend.app.core.exceptions import LLMAuthenticationError
from backend.app.llm.base import ChatMessage, MessageRole, ToolCall
from backend.app.llm.gemini import GeminiLLMClient, _dict_to_genai_schema


def test_gemini_client_auth_error():
    """Verify Gemini client raises LLMAuthenticationError when API key is empty."""
    with pytest.raises(LLMAuthenticationError):
        GeminiLLMClient(api_key="")


def test_gemini_schema_conversion():
    """Verify JSON schema dictionary conversion to types.Schema."""
    prop = {
        "type": "object",
        "description": "Calculation arguments",
        "properties": {
            "expression": {"type": "string", "description": "The math expression"},
            "precision": {"type": "integer", "description": "Decimal precision"}
        },
        "required": ["expression"]
    }
    schema = _dict_to_genai_schema(prop)
    assert schema.type == types.Type.OBJECT
    assert "expression" in schema.properties
    assert schema.properties["expression"].type == types.Type.STRING
    assert schema.properties["precision"].type == types.Type.INTEGER


def test_gemini_message_conversion_multi_tool():
    """
    Verify conversion of conversation history into Gemini Content turns.
    Ensures model turns include FunctionCalls and subsequent consecutive Tool turns
    are properly grouped into a single User turn.
    """
    client = GeminiLLMClient(api_key="fake-test-key-0000000000")

    messages = [
        ChatMessage(role=MessageRole.USER, content="What time is it in London and what is 50*2?"),
        ChatMessage(
            role=MessageRole.ASSISTANT,
            content=None,
            tool_calls=[
                ToolCall(id="c1", name="get_current_time", arguments={"timezone": "Europe/London"}),
                ToolCall(id="c2", name="calculator", arguments={"expression": "50 * 2"}),
            ]
        ),
        ChatMessage(role=MessageRole.TOOL, name="get_current_time", content='{"formatted": "15:00 BST"}'),
        ChatMessage(role=MessageRole.TOOL, name="calculator", content='{"result": 100}'),
    ]

    contents = client._convert_messages(messages)

    # Must produce 3 Content turns: User -> Model -> User (grouping both function responses)
    assert len(contents) == 3

    # Turn 1: User message
    assert contents[0].role == "user"
    assert contents[0].parts[0].text == "What time is it in London and what is 50*2?"

    # Turn 2: Model message with 2 function calls
    assert contents[1].role == "model"
    assert len(contents[1].parts) == 2
    assert contents[1].parts[0].function_call.name == "get_current_time"
    assert contents[1].parts[0].function_call.args["timezone"] == "Europe/London"
    assert contents[1].parts[1].function_call.name == "calculator"
    assert contents[1].parts[1].function_call.args["expression"] == "50 * 2"

    # Turn 3: User message grouping both function responses
    assert contents[2].role == "user"
    assert len(contents[2].parts) == 2
    assert contents[2].parts[0].function_response.name == "get_current_time"
    assert contents[2].parts[1].function_response.name == "calculator"
