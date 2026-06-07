import os
import anthropic

from core.ports.llm_provider import LLMProvider

DEFAULT_MODEL  = "claude-sonnet-4-6"
DEFAULT_TOKENS = 4096


class ClaudeAdapter(LLMProvider):
    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL):
        self.client = anthropic.Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
        self.model  = model

    def complete(self, prompt: str, system: str = "") -> str:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=DEFAULT_TOKENS,
            system=system or anthropic.NOT_GIVEN,
            messages=[{"role": "user", "content": prompt}],
        )
        if not message.content:
            return ""
        return message.content[0].text
