import ollama


class LLMProcessor:
    def __init__(self, default_model="llama3.2", host="http://localhost:11434"):
        """Initialize the LLM processor with a default model"""
        self.default_model = default_model
        self.client = ollama.Client(host=host)
        self.history = []

    def reset_history(self):
        """Clear conversation history"""
        self.history = []

    def chat(self, user_input, model=None):
        """Process user input, get LLM response, and update history"""
        model = model or self.default_model

        # Append user input to history
        self.history.append({"role": "user", "content": user_input})

        # Query the LLM
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

        # Append the assistant reply to history
        self.history.append({"role": "assistant", "content": assistant_reply})

        return assistant_reply

    def get_history(self):
        """Return the current conversation history"""
        return self.history.copy()

    def set_history(self, new_history):
        """Set a new conversation history"""
        self.history = new_history

    def add_system_prompt(self, system_prompt):
        """Add a system prompt at the beginning of the conversation"""
        # If history already has a system message, replace it
        if self.history and self.history[0].get("role") == "system":
            self.history[0] = {"role": "system", "content": system_prompt}
        # Otherwise, insert at the beginning
        else:
            self.history.insert(0, {"role": "system", "content": system_prompt})
