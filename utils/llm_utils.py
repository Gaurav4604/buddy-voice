import os
import json
from ollama import Client  # assuming ollama is installed and configured
from tools import play_search  # Register our tool

# Ensure VLC’s DLLs are in the search path (adjust path as needed)
os.add_dll_directory(r"C:\Program Files\VideoLAN\VLC")


class LLMProcessor:
    def __init__(self, default_model="llama3.2", host="http://localhost:11434"):
        self.default_model = default_model
        self.client = Client(host=host)
        self.history = []
        # Register available tools in a dictionary:
        self.tools = {"play_search": play_search}

    def reset_history(self):
        self.history = []

    def chat(self, user_input, model=None):
        """
        Sends the user input to the LLM and returns the assistant's reply.
        """
        model = model or self.default_model
        self.history.append({"role": "user", "content": user_input})
        try:
            response = self.client.chat(model=model, messages=self.history)
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

    def process_tool_command(self, command_payload: dict):
        """
        If the LLM output indicates a tool command, extract the tool name and its payload,
        then call the corresponding function.
        For example, if the payload is {"tool": "play_search", "query": "Never Gonna Give You Up"},
        then we call play_search("Never Gonna Give You Up").
        """
        tool_name = command_payload.get("tool")
        if tool_name in self.tools:
            func = self.tools[tool_name]
            # Assume that for play_search, the payload key is "query"
            query = command_payload.get("query", "")
            print(f"Invoking tool '{tool_name}' with query: {query}")
            func(query)
        else:
            print(f"No registered tool named '{tool_name}'.")

    def chat_and_auto_toolcall(self, user_input, model=None):
        """
        Sends a user input to the LLM and checks if the assistant's reply is a JSON payload
        representing a tool command. If so, auto-invokes the corresponding tool.
        Otherwise, returns the assistant's reply.
        """
        reply = self.chat(user_input, model=model)
        try:
            # Try parsing the assistant reply as JSON.
            command_payload = json.loads(reply)
            if isinstance(command_payload, dict) and "tool" in command_payload:
                print("Assistant returned a tool command payload.")
                self.process_tool_command(command_payload)
                return f"Tool '{command_payload.get('tool')}' executed."
            else:
                return reply
        except json.JSONDecodeError:
            # If the reply isn't JSON, return it as normal.
            return reply

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
