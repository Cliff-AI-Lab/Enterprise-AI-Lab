from collections.abc import AsyncIterator

from rd_llm_gateway.ports import LLMProvider
from rd_llm_gateway.types import ChatRequest, StreamChunk, StreamChunkType


class _StubProvider:
    async def stream_chat(
        self, req: ChatRequest
    ) -> AsyncIterator[StreamChunk]:
        async def gen():
            yield StreamChunk(
                seq=1, chunk_type=StreamChunkType.TEXT_DELTA, text="hi"
            )

        return gen()


def test_llm_provider_protocol():
    p: LLMProvider = _StubProvider()
    assert isinstance(p, LLMProvider)
