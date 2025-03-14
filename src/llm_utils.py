import os
import ollama
from ollama import Client, ChatResponse  # assuming ollama is installed and configured
from tools import play_music, capture_image_and_describe
from pydantic import BaseModel

# Ensure VLC’s DLLs are in the search path (adjust path as needed)
os.add_dll_directory(r"C:\Program Files\VideoLAN\VLC")


termination_message_check = """
check if this message suggests that the user wants to terminate the conversation
<message>
    {}
</message>
"""

check_user_action = """
# Action Decision Task

Analyze the user message below and determine which of the following actions is most appropriate based on the user's intent:

<message>
    {}
</message>

## Available Actions
- **capture_image_and_describe**: Select when the user wants to take a photo, get an image, or requests visual information about their surroundings. This includes:
  - Direct requests to take photos
  - Questions about what the user is showing or holding
  - Requests to see, look at, or identify objects
  - Questions asking if you can see something
  - Requests to describe what's visible
  - Any question that requires visual perception to answer

- **play_music**: Select when the user wants to listen to music, audio, or sound content. This includes:
  - Requests to play specific songs, artists, or genres
  - Commands to start, pause, or control audio playback
  - Queries about listening to music or sounds

- **text_response**: Select for general questions, information requests, or any intent not related to capturing images or playing music. This is the default option when no visual or audio action is required.

## Response Instructions
1. Prioritize visual intents - if the user is asking about something they're showing or holding, this requires image capture
2. Consider implied intents - phrases like "can you see this?" or "what do you think of this?" typically require visual perception
3. Choose the most appropriate action from the options above
4. Return only the action name, with no additional text
"""


REGISTERED_TOOLS = {
    "play_music": play_music,
    "capture_image_and_describe": capture_image_and_describe,
}


# @dataclass(frozen=True)
class TerminateConversation(BaseModel):
    should_terminate_conversation: bool


class DecideAction(BaseModel):
    action: str


class LLMProcessor:
    def __init__(self, default_model="llama3.2", host="http://localhost:11434"):
        self.default_model = default_model
        self.client = Client(host=host)
        self.history = []
        # Register available tools in a dictionary:
        self.tools = REGISTERED_TOOLS

    def reset_history(self):
        self.history = []

    def get_tool_support_for_chat(self, user_input: str):
        model = self.default_model

        response = ollama.chat(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": check_user_action.format(user_input),
                }
            ],
            format=DecideAction.model_json_schema(),
            options={"num_ctx": 4096},
        )

        llm_action = DecideAction.model_validate_json(response.message.content).action
        return llm_action

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
                    "content": termination_message_check.format(user_input),
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

        llm_action = self.get_tool_support_for_chat(user_input)

        llm_tools = []

        if llm_action == "play_music":
            llm_tools.append(REGISTERED_TOOLS["play_music"])
        elif llm_action == "capture_image_and_describe":
            llm_tools.append(REGISTERED_TOOLS["capture_image_and_describe"])

        self.history.append({"role": "user", "content": user_input})
        try:
            response: ChatResponse = self.client.chat(
                model=model,
                messages=self.history,
                options={
                    "num_ctx": 4096 if len(user_input) > 50 else 2048,
                    "temperature": 0.1,
                },
                tools=llm_tools,
            )

            tool_calls = response.message.get("tool_calls", [])

            if tool_calls:
                for tool_call in tool_calls:
                    tool_res = self.execute_tool_call(tool_call)
                    if tool_res:
                        self.history.append(
                            {
                                "role": "tool",
                                "content": tool_res,
                            }
                        )
                        response: ChatResponse = self.client.chat(
                            model=model,
                            messages=self.history,
                            options={
                                "temperature": 0.1,
                            },
                            tools=llm_tools,
                        )
                    else:
                        self.history.append(
                            {"role": "tool", "content": "Playing the requested Song"}
                        )
                        self.history.append(
                            {"role": "assistant", "content": "Finished Playing Song"}
                        )
                        return "Tool call executed."

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
    # output = processor.chat_and_auto_toolcall(user_input)
    # print("Final output:", output)
    output = processor.chat(user_input)
    print(output)

    user_input = "can you see what I'm holding right now?"
    output = processor.chat(user_input)
    print(output)

    user_input = "what is tiktok?"
    output = processor.chat(user_input)
    print(output)
