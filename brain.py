import os
from langchain_anthropic import ChatAnthropic
def make_brain(temperature=0.7, max_tokens=2048):
 """Return a ready-to-use model connected to the class LLM."""
 token = os.environ["ANTHROPIC_AUTH_TOKEN"]
 return ChatAnthropic(
 model=os.environ.get("ANTHROPIC_MODEL", "qwen3.6-27b"),
 base_url=os.environ["ANTHROPIC_BASE_URL"],
 api_key=token,
 default_headers={"Authorization": f"Bearer {token}"},
 temperature=temperature,
 max_tokens=max_tokens,
 )
if __name__ == "__main__":
 brain = make_brain()
 print(brain.invoke("Say hello to the class in one sentence.").text)
