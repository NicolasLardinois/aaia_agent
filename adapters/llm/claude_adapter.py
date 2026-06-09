import os
import anthropic

from core.ports.llm_provider import LLMProvider

DEFAULT_MODEL  = "claude-sonnet-4-6"
DEFAULT_TOKENS = 4096
MAX_RETRIES    = 2


class ClaudeAdapter(LLMProvider):
    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL):
        self.client = anthropic.Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
        self.model  = model

    def complete(self, prompt: str, system: str = "") -> str:
        import time
        for attempt in range(MAX_RETRIES + 1):
            try:
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=DEFAULT_TOKENS,
                    system=system or anthropic.NOT_GIVEN,
                    messages=[{"role": "user", "content": prompt}],
                )
                if message.content:
                    return message.content[0].text
            except Exception:
                pass
            if attempt < MAX_RETRIES:
                time.sleep(1)
        return ""
