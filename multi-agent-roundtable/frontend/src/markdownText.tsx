import { Music2 } from "lucide-react";
import { memo, useMemo } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { AudioPlayer } from "./AudioPlayer";

export type MarkdownImage = {
  src: string;
  alt: string;
};

// 只允许同源 backend media 路由（chat messages 或 Moments posts）。
// 挡掉 javascript: / data: / 外链 / 任意路径注入。
// 尾部扩展名可选：图片旧消息无扩展名（默认 .png），音频/未来格式带 .mp3/.wav/.flac/etc。
const MEDIA_SRC_RE = /^\/api\/(messages|posts)\/[a-z0-9_-]+\/media\/\d+(\.[a-z0-9]+)?$/i;
// 只允许 https 外链；挡 http / javascript: / data: 等。
const SAFE_HREF_RE = /^https:\/\/[^\s<>"']+$/;

const AUDIO_EXT_RE = /\.(mp3|wav|ogg|m4a)$/i;
const VIDEO_EXT_RE = /\.(mp4|webm|mov)$/i;
const REMARK_PLUGINS = [remarkGfm];

export const MarkdownText = memo(function MarkdownText({
  children,
  onImageClick,
  skipImages = false,
}: {
  children: string;
  onImageClick?: (image: MarkdownImage) => void;
  skipImages?: boolean;
}) {
  const components = useMemo<Components>(
    () => ({
      p({ node, children }) {
        const nodeChildren = node?.children ?? [];
        const onlyChild = nodeChildren.length === 1 ? nodeChildren[0] : undefined;
        if (onlyChild?.type === "element" && onlyChild.tagName === "img") {
          return <>{children}</>;
        }
        return <p>{children}</p>;
      },
      a({ href, children }) {
        if (typeof href === "string" && SAFE_HREF_RE.test(href)) {
          return (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer nofollow"
              className="markdown-link"
            >
              {children}
            </a>
          );
        }
        return <>{children}</>;
      },
      img({ src, alt }) {
        if (typeof src !== "string" || !MEDIA_SRC_RE.test(src)) return null;
        if (skipImages) return null;
        const altText = alt ?? "";
        if (AUDIO_EXT_RE.test(src)) {
          return (
            <div className="markdown-audio-card" role="group" aria-label={altText || "音频"}>
              <div className="audio-card-head">
                <span className="audio-card-icon" aria-hidden="true">
                  <Music2 size={14} strokeWidth={2.2} />
                </span>
                <span className="audio-card-title">{altText || "音频"}</span>
              </div>
              <AudioPlayer src={src} label={altText || "音频"} className="markdown-audio" />
            </div>
          );
        }
        if (VIDEO_EXT_RE.test(src)) {
          return <video controls preload="metadata" src={src} className="markdown-video" />;
        }
        if (onImageClick) {
          return (
            <button
              aria-label={altText ? `查看图片：${altText}` : "查看图片"}
              className="markdown-image-button"
              onClick={() => onImageClick({ src, alt: altText })}
              type="button"
            >
              <img src={src} alt={altText} loading="lazy" className="markdown-image" />
            </button>
          );
        }
        return <img src={src} alt={altText} loading="lazy" className="markdown-image" />;
      },
      table({ children }) {
        return <table className="markdown-table">{children}</table>;
      },
    }),
    [onImageClick, skipImages],
  );

  return (
    <div className="markdown-text">
      <ReactMarkdown remarkPlugins={REMARK_PLUGINS} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  );
});
