"""Chat analysis powered by Google Gemini."""

from google import genai

from chatlens import config

# ponytail: hard-coded chunk size; good enough for gemini-2.0-flash context window.
# Upgrade path: estimate tokens instead of message count.
_CHUNK_SIZE = 800


def _format_messages(messages: list[dict]) -> str:
    """Format messages as 'SENDER (TIMESTAMP): TEXT', one per line."""
    lines = []
    for m in messages:
        sender = m.get("sender", "?")
        ts = m.get("timestamp", "")
        text = m.get("text", "")
        lines.append(f"{sender} ({ts}): {text}")
    return "\n".join(lines)


class ChatAnalyzer:
    def __init__(self):
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY must be set in .env")
        self._client = genai.Client(api_key=config.GEMINI_API_KEY)
        self._model = config.GEMINI_MODEL

    def _call_gemini(self, prompt: str) -> str:
        """Send a prompt to Gemini and return the text response."""
        response = self._client.models.generate_content(
            model=self._model, contents=prompt
        )
        return response.text

    def summarize(self, messages: list[dict]) -> str:
        """Summarize a conversation. Chunks large conversations by time windows."""
        if len(messages) <= _CHUNK_SIZE:
            transcript = _format_messages(messages)
            return self._call_gemini(
                f"Summarize this chat conversation concisely. "
                f"Highlight key topics, decisions, and action items.\n\n{transcript}"
            )

        # Chunk and summarize individually, then meta-summarize
        chunk_summaries = []
        for i in range(0, len(messages), _CHUNK_SIZE):
            chunk = messages[i : i + _CHUNK_SIZE]
            transcript = _format_messages(chunk)
            summary = self._call_gemini(
                f"Summarize this segment of a chat conversation concisely:\n\n{transcript}"
            )
            chunk_summaries.append(summary)

        combined = "\n\n---\n\n".join(
            f"Segment {i + 1}:\n{s}" for i, s in enumerate(chunk_summaries)
        )
        return self._call_gemini(
            f"Below are summaries of consecutive segments of the same conversation. "
            f"Produce a single unified summary covering all key topics, decisions, "
            f"and action items.\n\n{combined}"
        )

    def analyze_sentiment(self, messages: list[dict]) -> str:
        """Analyze sentiment across the conversation."""
        transcript = _format_messages(messages[-_CHUNK_SIZE:])
        return self._call_gemini(
            f"Analyze the sentiment of this chat conversation. "
            f"Describe the overall tone, emotional shifts, and notable emotional moments. "
            f"Identify per-participant sentiment where possible.\n\n{transcript}"
        )

    def extract_topics(self, messages: list[dict]) -> str:
        """Extract key topics discussed."""
        transcript = _format_messages(messages[-_CHUNK_SIZE:])
        return self._call_gemini(
            f"Extract the key topics and themes discussed in this chat conversation. "
            f"List each topic with a brief description.\n\n{transcript}"
        )

    def map_relationships(self, messages: list[dict]) -> str:
        """Analyze who talks to whom, frequency, and dynamics."""
        transcript = _format_messages(messages[-_CHUNK_SIZE:])
        return self._call_gemini(
            f"Analyze the social dynamics in this chat conversation. "
            f"Who talks to whom most? What are the interaction patterns? "
            f"Who are the most active participants? Describe the group dynamics.\n\n{transcript}"
        )

    def extract_timeline(self, messages: list[dict]) -> str:
        """Extract key events with dates."""
        transcript = _format_messages(messages[-_CHUNK_SIZE:])
        return self._call_gemini(
            f"Extract a timeline of key events, decisions, and milestones "
            f"from this chat conversation. Include dates where available.\n\n{transcript}"
        )

    def ask(self, question: str, context_messages: list[dict]) -> str:
        """Answer a question using message context."""
        transcript = _format_messages(context_messages[-_CHUNK_SIZE:])
        return self._call_gemini(
            f"Based on the following chat conversation, answer this question:\n\n"
            f"Question: {question}\n\n"
            f"Conversation:\n{transcript}"
        )

    def full_analysis(self, messages: list[dict]) -> dict:
        """Run all analyses and return results as a dict."""
        return {
            "summary": self.summarize(messages),
            "sentiment": self.analyze_sentiment(messages),
            "topics": self.extract_topics(messages),
            "relationships": self.map_relationships(messages),
            "timeline": self.extract_timeline(messages),
        }
