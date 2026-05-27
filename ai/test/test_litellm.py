import os
from dotenv import load_dotenv
load_dotenv()

import litellm

response = litellm.completion(
    model=os.getenv("MODEL_NAME"),
    messages=[{"role": "user", "content": "Say hello in exactly 5 words."}],
    max_tokens=50,
)
print(response.choices[0].message.content)