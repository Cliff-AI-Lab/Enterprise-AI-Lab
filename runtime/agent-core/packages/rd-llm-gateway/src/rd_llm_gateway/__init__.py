"""rd-llm-gateway — LLMProvider + adapters + stream chunk normalizer。"""

from .adapters.openai_compat import OpenAICompatProvider
from .normalizer import StreamNormalizer
from .ports import LLMProvider
from .types import ChatRequest, StreamChunk, StreamChunkType

__version__ = "1.0.0"

__all__ = [
    "ChatRequest",
    "LLMProvider",
    "OpenAICompatProvider",
    "StreamChunk",
    "StreamChunkType",
    "StreamNormalizer",
]
