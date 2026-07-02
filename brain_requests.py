import os, requests
BASE_URL = os.environ["ANTHROPIC_BASE_URL"]
TOKEN = os.environ["ANTHROPIC_AUTH_TOKEN"]
MODEL = os.environ.get("ANTHROPIC_MODEL", "qwen3.6-27b")
def ask(question, max_tokens=1024):
 r = requests.post(
 f"{BASE_URL}/v1/messages",
 headers={
 "Authorization": f"Bearer {TOKEN}", # <-- this server needs Bearer
 "anthropic-version": "2023-06-01",
 "content-type": "application/json",
 },
 json={
 "model": MODEL,
 "max_tokens": max_tokens,
 "messages": [{"role": "user", "content": question}],
 },
 timeout=120,
 )
 r.raise_for_status()
 blocks = r.json()["content"]
 # keep only the real answer text (this model also returns a "thinking" block)
 return "".join(b["text"] for b in blocks if b.get("type") == "text").strip()
if __name__ == "__main__":
 print(ask("Write one short beginner question about Python lists."))
