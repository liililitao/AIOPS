import hashlib
import os
from openai import OpenAI
client = OpenAI(
    base_url="https://api.marketplace.novo-genai.com/v1",
    api_key=os.getenv("LLM_API_KEY", "")
    )
user_id = hashlib.sha256(os.getenv("LLM_USER_EMAIL", "").encode()).hexdigest()
# print("User ID:", user_id)
response = client.chat.completions.create(
    model="openai_gpt5", 
    messages=[{
        "role": "user", 
        "content": 
            "你好"
    }], 
    user=user_id
    )
print(response.choices[0].message.content)
