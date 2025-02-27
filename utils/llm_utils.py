import os
import json
import ollama
from ollama import Client, ChatResponse  # assuming ollama is installed and configured
from utils.tools import play_music
from pydantic import BaseModel

# Ensure VLC’s DLLs are in the search path (adjust path as needed)
os.add_dll_directory(r"C:\Program Files\VideoLAN\VLC")


REGISTERED_TOOLS = {"play_music": play_music}


# @dataclass(frozen=True)
class TerminateConversation(BaseModel):
    should_terminate_conversation: bool


class LLMProcessor:
    def __init__(self, default_model="llama3.2", host="http://localhost:11434"):
        self.default_model = default_model
        self.client = Client(host=host)
        self.history = []
        # Register available tools in a dictionary:
        self.tools = REGISTERED_TOOLS

    def reset_history(self):
        self.history = []

    def chat(self, user_input, model=None):
        """
        Sends the user input to the LLM and returns the assistant's reply.
        """
        model = model or self.default_model

        response = ollama.chat(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": f"""check if this message suggests that the user whats to terminate the conversation
                        <message>
                            {user_input}
                        </message>
                    """,
                }
            ],
            format=TerminateConversation.model_json_schema(),
            options={"num_ctx": 1024},
        )

        terminate = TerminateConversation.model_validate_json(
            response.message.content
        ).should_terminate_conversation

        if terminate:
            return ""

        self.history.append({"role": "user", "content": user_input})
        try:
            response: ChatResponse = self.client.chat(
                model=model,
                messages=self.history,
                options={"num_ctx": 4096 if len(user_input) > 50 else 2048},
                tools=list(self.tools.values()),
            )

            tool_calls = response.message.get("tool_calls", [])

            print(response)

            if tool_calls:
                for tool_call in tool_calls:
                    self.execute_tool_call(tool_call)
                return "Tool call(s) executed."

            assistant_reply = response.message.get(
                "content", "Sorry, I did not understand that."
            )
        except Exception as e:
            print(f"Error querying LLM: {e}")
            assistant_reply = (
                "I'm having trouble connecting to the language model. Please try again."
            )
        self.history.append({"role": "assistant", "content": assistant_reply})
        return assistant_reply

    def execute_tool_call(self, tool_call):
        """
        Execute a tool call from the assistant's response.
        The tool_call is expected to have the structure:
        ToolCall(function=Function(name='play_search', arguments={'query': 'song name'}))
        """
        try:
            tool_name = tool_call.function.name
            arguments = tool_call.function.arguments  # should be a dict
        except AttributeError:
            print("Invalid tool call structure.")
            return

        if tool_name in self.tools:
            func = self.tools[tool_name]
            print(f"Auto-executing tool '{tool_name}' with arguments: {arguments}")
            # Call the function with the arguments unpacked
            return func(**arguments)
        else:
            print(f"No registered tool named '{tool_name}'.")
            return

    def get_history(self):
        return self.history.copy()

    def set_history(self, new_history):
        self.history = new_history

    def add_system_prompt(self, system_prompt):
        if self.history and self.history[0].get("role") == "system":
            self.history[0] = {"role": "system", "content": system_prompt}
        else:
            self.history.insert(0, {"role": "system", "content": system_prompt})


# Example usage:
if __name__ == "__main__":
    processor = LLMProcessor()
    # In practice, instruct your LLM (via a system prompt) to output tool commands as JSON.
    # For demonstration, simulate a user input and assume the assistant returns a tool command.
    user_input = "Play Never Gonna Give You Up"
    output = processor.chat_and_auto_toolcall(user_input)
    print("Final output:", output)
