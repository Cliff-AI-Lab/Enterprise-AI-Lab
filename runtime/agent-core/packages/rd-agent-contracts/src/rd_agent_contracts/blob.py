"""BlobRef — 大工具输出的 reference 协议。

P6 executor middleware 根据阈值决定 inline / truncated+ref / pure ref。
P5/P9 依赖此字段做 transcript 与 replay。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BlobRef:
    content_bytes: int
    content_sha256: str
    mime_type: str
    content_inline: str | None = None
    content_ref: str | None = None
    content_inline_truncated: bool = False

    def __post_init__(self) -> None:
        if self.content_inline is None and self.content_ref is None:
            raise ValueError(
                "BlobRef requires at least one of content_inline or content_ref"
            )

    def is_inline(self) -> bool:
        return (
            self.content_inline is not None
            and not self.content_inline_truncated
            and self.content_ref is None
        )
