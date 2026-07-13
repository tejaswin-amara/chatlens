"""Chat analysis powered by Google Gemini."""

import asyncio

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

    async def _call_gemini_async(self, prompt: str) -> str:
        """Send a prompt to Gemini asynchronously and return the text response."""
        if hasattr(self._client, "aio"):
            response = await self._client.aio.models.generate_content(
                model=self._model, contents=prompt
            )
            return response.text
        return await asyncio.to_thread(self._call_gemini, prompt)

    @staticmethod
    def _run(coro):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        raise RuntimeError(
            "Synchronous ChatAnalyzer methods cannot be used inside an active event loop. "
            "Use async methods instead."
        )

    async def summarize_async(self, messages: list[dict]) -> str:
        """Summarize a conversation. Chunks large conversations by time windows."""
        if len(messages) <= _CHUNK_SIZE:
            transcript = _format_messages(messages)
            return await self._call_gemini_async(
                f"Summarize this chat conversation concisely. "
                f"Highlight key topics, decisions, and action items.\n\n{transcript}"
            )

        # Chunk and summarize individually, then meta-summarize
        chunk_summaries = []
        for i in range(0, len(messages), _CHUNK_SIZE):
            chunk = messages[i : i + _CHUNK_SIZE]
            transcript = _format_messages(chunk)
            summary = await self._call_gemini_async(
                f"Summarize this segment of a chat conversation concisely:\n\n{transcript}"
            )
            chunk_summaries.append(summary)

        combined = "\n\n---\n\n".join(
            f"Segment {i + 1}:\n{s}" for i, s in enumerate(chunk_summaries)
        )
        return await self._call_gemini_async(
            f"Below are summaries of consecutive segments of the same conversation. "
            f"Produce a single unified summary covering all key topics, decisions, "
            f"and action items.\n\n{combined}"
        )

    async def analyze_sentiment_async(self, messages: list[dict]) -> str:
        """Analyze sentiment across the conversation."""
        transcript = _format_messages(messages[-_CHUNK_SIZE:])
        return await self._call_gemini_async(
            f"Analyze the sentiment of this chat conversation. "
            f"Describe the overall tone, emotional shifts, and notable emotional moments. "
            f"Identify per-participant sentiment where possible.\n\n{transcript}"
        )

    async def extract_topics_async(self, messages: list[dict]) -> str:
        """Extract key topics discussed."""
        transcript = _format_messages(messages[-_CHUNK_SIZE:])
        return await self._call_gemini_async(
            f"Extract the key topics and themes discussed in this chat conversation. "
            f"List each topic with a brief description.\n\n{transcript}"
        )

    async def map_relationships_async(self, messages: list[dict]) -> str:
        """Analyze who talks to whom, frequency, and dynamics."""
        transcript = _format_messages(messages[-_CHUNK_SIZE:])
        return await self._call_gemini_async(
            f"Analyze the social dynamics in this chat conversation. "
            f"Who talks to whom most? What are the interaction patterns? "
            f"Who are the most active participants? Describe the group dynamics.\n\n{transcript}"
        )

    async def extract_timeline_async(self, messages: list[dict]) -> str:
        """Extract key events with dates."""
        transcript = _format_messages(messages[-_CHUNK_SIZE:])
        return await self._call_gemini_async(
            f"Extract a timeline of key events, decisions, and milestones "
            f"from this chat conversation. Include dates where available.\n\n{transcript}"
        )

    async def ask_async(self, question: str, context_messages: list[dict]) -> str:
        """Answer a question using message context."""
        transcript = _format_messages(context_messages[-_CHUNK_SIZE:])
        return await self._call_gemini_async(
            f"Based on the following chat conversation, answer this question:\n\n"
            f"Question: {question}\n\n"
            f"Conversation:\n{transcript}"
        )

    async def full_analysis_async(self, messages: list[dict]) -> dict:
        """Run all analyses and return results as a dict."""
        return {
            "summary": await self.summarize_async(messages),
            "sentiment": await self.analyze_sentiment_async(messages),
            "topics": await self.extract_topics_async(messages),
            "relationships": await self.map_relationships_async(messages),
            "timeline": await self.extract_timeline_async(messages),
        }

    def summarize(self, messages: list[dict]) -> str:
        return self._run(self.summarize_async(messages))

    def analyze_sentiment(self, messages: list[dict]) -> str:
        return self._run(self.analyze_sentiment_async(messages))

    def extract_topics(self, messages: list[dict]) -> str:
        return self._run(self.extract_topics_async(messages))

    def map_relationships(self, messages: list[dict]) -> str:
        return self._run(self.map_relationships_async(messages))

    def extract_timeline(self, messages: list[dict]) -> str:
        return self._run(self.extract_timeline_async(messages))

    def ask(self, question: str, context_messages: list[dict]) -> str:
        return self._run(self.ask_async(question, context_messages))

    def full_analysis(self, messages: list[dict]) -> dict:
        return self._run(self.full_analysis_async(messages))
