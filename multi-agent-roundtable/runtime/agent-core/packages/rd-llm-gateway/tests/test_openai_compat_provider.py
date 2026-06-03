"""验证 OpenAICompatProvider 能完整处理一次流式调用。"""
import pytest
import respx
from httpx import Response
from rd_llm_gateway.adapters.openai_compat import OpenAICompatProvider
from rd_llm_gateway.types import ChatRequest, StreamChunkType

_SSE_BODY = (
    b'data: {"choices":[{"delta":{"content":"hello"},"finish_reason":null}]}\n\n'
    b'data: {"choices":[{"delta":{"content":" world"},"finish_reason":null}]}\n\n'
    b'data: {"choices":[{"delta":{},"finish_reason":"stop"}],'
    b'"usage":{"prompt_tokens":10,"completion_tokens":5}}\n\n'
    b"data: [DONE]\n\n"
)


@pytest.mark.asyncio
async def test_stream_chat_basic():
    async with respx.mock(assert_all_called=True) as router:
        router.post("https://api.openai.test/v1/chat/completions").mock(
            return_value=Response(
                200,
                content=_SSE_BODY,
                headers={"content-type": "text/event-stream"},
            )
        )

        provider = OpenAICompatProvider(
            base_url="https://api.openai.test/v1",
            api_key="sk-test",
        )
        req = ChatRequest(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
            max_tokens=100,
        )

        chunks = []
        async for c in await provider.stream_chat(req):
            chunks.append(c)

        text_chunks = [
            c for c in chunks if c.chunk_type is StreamChunkType.TEXT_DELTA
        ]
        assert len(text_chunks) == 2
        assert text_chunks[0].text == "hello"
        assert text_chunks[1].text == " world"

        usage_chunks = [
            c for c in chunks if c.chunk_type is StreamChunkType.USAGE
        ]
        assert len(usage_chunks) == 1
        assert usage_chunks[0].usage.input_tokens == 10
        assert usage_chunks[0].usage.output_tokens == 5

        # seq 单调递增
        seqs = [c.seq for c in chunks]
        assert seqs == sorted(seqs)
        assert seqs[0] == 1
