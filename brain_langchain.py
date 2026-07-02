import os
from langchain_anthropic import ChatAnthropic
TOKEN = os.environ["ANTHROPIC_AUTH_TOKEN"]
llm = ChatAnthropic(
 model=os.environ.get("ANTHROPIC_MODEL", "qwen3.6-27b"),
 base_url=os.environ["ANTHROPIC_BASE_URL"],
 api_key=TOKEN,
 # This server authenticates with a Bearer header; the Anthropic SDK
 # normally sends x-api-key, so we add the header ourselves:
 default_headers={"Authorization": f"Bearer {TOKEN}"},
 temperature=0.7,
 max_tokens=2048, # leave room: this model "thinks" before it answers
)
reply = llm.invoke("Write one short beginner question about Python lists.")
print(reply.text) # .text = just the answer (not the hidden reasoning)
