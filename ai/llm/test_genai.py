import os
import litellm
from dotenv import load_dotenv

load_dotenv()

# Initialize the chat history array
chat_history = []

def chat_with_assistant(user_message: str):
    # 1. Append the new user prompt to history
    chat_history.append({"role": "user", "content": user_message})
    
    # 2. Call the SAP gpt-4o model via LiteLLM
    response = litellm.completion(
        model="sap/gpt-4o",
        messages=chat_history
    )
    
    assistant_reply = response.choices[0].message.content
    
    # 3. Append the assistant's answer to keep context for the next turn
    chat_history.append({"role": "assistant", "content": assistant_reply})
    
    return assistant_reply

# Example usage:
print(chat_with_assistant("My package ID is APTIV-9981."))
print(chat_with_assistant("Where is it shipping from?"))  # The model remembers the ID!
