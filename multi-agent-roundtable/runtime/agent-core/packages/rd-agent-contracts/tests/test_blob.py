import pytest
from rd_agent_contracts.blob import BlobRef


def test_blob_ref_inline():
    """小输出走 inline。"""
    b = BlobRef(
        content_inline="hello world",
        content_bytes=11,
        content_sha256="b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9",
        mime_type="text/plain",
    )
    assert b.is_inline()
    assert b.content_inline == "hello world"


def test_blob_ref_external():
    """大输出走 ref。"""
    b = BlobRef(
        content_ref="s3://bucket/path",
        content_bytes=10_000_000,
        content_sha256="abc123",
        mime_type="application/octet-stream",
    )
    assert not b.is_inline()
    assert b.content_ref == "s3://bucket/path"


def test_blob_ref_truncated():
    """中等输出：inline 截断 + 标记 truncated。"""
    b = BlobRef(
        content_inline="(...truncated)",
        content_inline_truncated=True,
        content_ref="s3://bucket/full",
        content_bytes=500_000,
        content_sha256="def456",
        mime_type="text/plain",
    )
    assert b.content_inline_truncated is True
    assert b.content_ref is not None


def test_blob_ref_at_least_one_source():
    """inline 和 ref 至少有一个非空。"""
    with pytest.raises(ValueError, match="content_inline.*content_ref"):
        BlobRef(content_bytes=0, content_sha256="x", mime_type="text/plain")
