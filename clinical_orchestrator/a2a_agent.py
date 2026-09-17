"""Custom A2aAgent subclass enforcing HTTPS transport scheme on Agent Runtime."""

from vertexai.preview.reasoning_engines import A2aAgent


class SecureA2aAgent(A2aAgent):
    """Subclass of A2aAgent enforcing https:// scheme on container setup and card discovery."""

    def set_up(self) -> None:
        super().set_up()
        if (
            hasattr(self, "agent_card")
            and self.agent_card
            and getattr(self.agent_card, "url", None)
        ):
            if self.agent_card.url.startswith("http://"):
                self.agent_card.url = "https://" + self.agent_card.url[7:]

    def handle_authenticated_agent_card(self, *args, **kwargs):
        card = super().handle_authenticated_agent_card(*args, **kwargs)
        if hasattr(card, "url") and card.url and card.url.startswith("http://"):
            card.url = "https://" + card.url[7:]
        return card