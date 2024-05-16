import anthropic
import os 

anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
client = anthropic.Anthropic(api_key=anthropic_api_key)

message = client.messages.create(
    model="claude-3-opus-20240229",
    max_tokens=1000,
    temperature=0.0,
    system="Respond only in Yoda-speak.",
    messages=[
        {"role": "user", "content": "How are you today?"}
]
)

print(message.content)