"""Chat analysis powered by Google Gemini."""

from google import genai

import config
from google.genai.errors import ClientError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
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

    @retry(
        retry=retry_if_exception_type(ClientError),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5)
    )
    def _call_gemini(self, prompt: str) -> str:
        """Send a prompt to Gemini and return the text response with backoff."""
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

    def generate_insight(self, insight_type: str, messages: list[dict]) -> str:
        """Generate specific 'Insight Modes' using custom AI prompts."""
        transcript = _format_messages(messages[-_CHUNK_SIZE:])
        
        prompts = {
            "relationship_dynamics": (
                "You are an expert behavioral psychologist. Analyze the relationship dynamics in this chat.\n"
                "Focus on:\n"
                "1. Power balance (who drives the conversation, who follows).\n"
                "2. Communication styles (direct, passive, emotional, logical).\n"
                "3. Mutual engagement (are both parties equally invested?).\n"
                "4. Inside jokes or shared context observed.\n"
                "Format as a Markdown report with emojis."
            ),
            "vibe_check": (
                "You are a Gen-Z internet culture expert. Give a 'Vibe Check' of this chat.\n"
                "Focus on:\n"
                "1. Overall Energy (chaotic, wholesome, dry, toxic, professional).\n"
                "2. Humor style (sarcastic, goofy, dark, none).\n"
                "3. Emotional shifts over time.\n"
                "4. A final 'Vibe Score' out of 10 with a funny explanation.\n"
                "Format as a Markdown report with emojis."
            ),
            "flags": (
                "You are an objective relationship counselor. Analyze this chat for Red Flags and Green Flags.\n"
                "Focus on:\n"
                "1. Green Flags: supportive language, active listening, validation, respectful boundaries.\n"
                "2. Red Flags: passive-aggressiveness, dismissive behavior, manipulation, or constant negativity.\n"
                "3. A brief summary of communication health.\n"
                "Format as a Markdown report with clear '🟢 Green Flags' and '🔴 Red Flags' sections."
            ),
            "recap": (
                "Provide a comprehensive but concise TL;DR (Too Long; Didn't Read) recap of this chat.\n"
                "Focus on:\n"
                "1. The main overarching narrative.\n"
                "2. Key decisions made or arguments resolved.\n"
                "3. A funny or notable quote from the chat (if any).\n"
                "Format as a Markdown report."
            )
        }
        
        prompt = prompts.get(insight_type)
        if not prompt:
            raise ValueError(f"Unknown insight type: {insight_type}")
            
        return self._call_gemini(f"{prompt}\n\nConversation Transcript:\n{transcript}")

