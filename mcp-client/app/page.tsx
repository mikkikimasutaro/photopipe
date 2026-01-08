"use client";

import { useMemo, useState } from "react";

type Msg = { role: "user" | "assistant"; content: string };
type MediaItem = {
  path: string;
  type: "image" | "video";
  mime?: string;
  name?: string;
};

const URL_RE = /(https?:\/\/[^\s]+)/;
const URL_SPLIT_RE = /(https?:\/\/[^\s]+)/g;
const MEDIA_BLOCK_RE = /\[\[media\]\]([\s\S]*?)\[\[\/media\]\]/g;

function renderWithLinks(text: string) {
  const parts = text.split(URL_SPLIT_RE);
  return parts.map((part, i) =>
    URL_RE.test(part) ? (
      <a key={`url-${i}`} href={part} target="_blank" rel="noreferrer">
        {part}
      </a>
    ) : (
      <span key={`txt-${i}`}>{part}</span>
    )
  );
}

function extractMediaBlocks(text: string) {
  const media: MediaItem[] = [];
  let cleaned = text;

  cleaned = cleaned.replace(MEDIA_BLOCK_RE, (match, payload) => {
    try {
      let trimmed = String(payload).trim();
      if (trimmed.startsWith("```")) {
        trimmed = trimmed.replace(/```(?:json)?/g, "").trim();
      }
      const parsed = JSON.parse(trimmed);
      if (
        parsed &&
        typeof parsed.path === "string" &&
        (parsed.type === "image" || parsed.type === "video")
      ) {
        media.push({
          path: parsed.path,
          type: parsed.type,
          mime: typeof parsed.mime === "string" ? parsed.mime : undefined,
          name: typeof parsed.name === "string" ? parsed.name : undefined,
        });
        return "";
      }
    } catch {
      // Keep the original block if parsing fails.
    }
    return match;
  });

  return { text: cleaned.trim(), media };
}

export default function Home() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: "assistant",
      content:""
    },
  ]);
  const [busy, setBusy] = useState(false);

  const canSend = useMemo(() => input.trim().length > 0 && !busy, [input, busy]);

  async function send() {
    if (!canSend) return;
    const userMsg: Msg = { role: "user", content: input.trim() };
    const next = [...messages, userMsg];
    setMessages(next);
    setInput("");
    setBusy(true);

    try {
      const r = await fetch("/api/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ messages: next }),
      });

      const raw = await r.text();
      let data: any = {};
      try {
        data = raw ? JSON.parse(raw) : {};
      } catch {
        data = { error: raw || `Non-JSON response (status ${r.status})` };
      }

      const a: Msg = {
        role: "assistant",
        content:
          data.text ??
          data.error ??
          (raw ? raw : `Empty response (status ${r.status})`),
      };
      setMessages([...next, a]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="page">
      <div className="bg-blob amber" />
      <div className="bg-blob mint" />
      <div className="bg-blob sky" />

      <div className="container">
        <header className="hero">
          <h1>ローカルメディアエージェント（デモ）</h1>
          <p className="sub">
             ・ 写真・動画を含むディレクトリを検索できます。例: Capturesを検索
          </p>
          <p className="sub">
             ・ 指定したディレクトリの写真・動画ファイルの一覧を表示できます。例: C:\Users\J0115990\Desktop\NodeScripts\photoviewer\samplephotos内のメディア一覧を表示して。
          </p>
          <p className="sub">
             ・ フルパスの写真/動画を指定して、チャット内で表示・再生できます。例: C:\Users\J0115990\Videos\Captures\2024-09-20 17-56-19.mp4 を再生して。）
          </p>
          <p className="sub">
             ・ スマホ閲覧用に写真をリサイズして一括アップロードできます。例: C:\Users\J0115990\Desktop\NodeScripts\photoviewer\samplephotos を samplephotosにアップロードして。デモなのでdry-runで空実行して。
          </p>
        </header>

        <section className="chat-card">
          <div className="chat-title">セッション</div>
          <div className="chat-body">
            {messages.map((m, i) => (
              <div key={i} className={m.role === "user" ? "msg right" : "msg left"}>
                <div className={m.role === "user" ? "bubble user" : "bubble assistant"}>
                  {(() => {
                    const { text, media } = extractMediaBlocks(m.content);
                    return (
                      <>
                        {text ? renderWithLinks(text) : null}
                        {media.map((item, idx) => {
                          const src = `/api/media?path=${encodeURIComponent(item.path)}`;
                          return (
                            <div key={`${item.path}-${idx}`} className="media">
                              {item.type === "image" ? (
                                <img src={src} alt={item.name ?? "image"} />
                              ) : (
                                <video src={src} controls preload="metadata" />
                              )}
                              <div className="media-caption">
                                {item.name ?? item.path}
                              </div>
                            </div>
                          );
                        })}
                      </>
                    );
                  })()}
                </div>
              </div>
            ))}
            {busy && <div className="status">処理中…</div>}
          </div>
        </section>
      </div>

      <div className="composer-wrap">
        <div className="composer">
          <button className="icon-btn" type="button" aria-label="Add">
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
              <path
                d="M12 5v14M5 12h14"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
          </button>
          <input
            className="composer-input"
            placeholder="依頼内容を入力…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            disabled={busy}
          />
          <button
            className="send-btn"
            onClick={send}
            disabled={!canSend}
            aria-label="Send"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
              <path
                d="M12 4v12M7 9l5-5 5 5"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>
      </div>

      <style jsx>{`
        .page {
          min-height: 100vh;
          padding: 32px 20px 120px;
          position: relative;
          background: radial-gradient(1200px circle at 20% -10%, #fff0d8 0%, transparent 60%),
            radial-gradient(900px circle at 110% 10%, #e6f6f0 0%, transparent 55%),
            linear-gradient(180deg, #f9f6f1 0%, #f2f5f4 60%, #f7f3ee 100%);
          color: #111;
          font-family: "Space Grotesk", "Noto Sans JP", "Helvetica Neue", Arial, sans-serif;
        }

        .bg-blob {
          position: fixed;
          filter: blur(60px);
          opacity: 0.7;
          border-radius: 999px;
          z-index: -1;
        }
        .bg-blob.amber {
          width: 280px;
          height: 280px;
          top: -120px;
          left: -60px;
          background: #ffd9a8;
        }
        .bg-blob.mint {
          width: 320px;
          height: 320px;
          top: 40px;
          right: -80px;
          background: #c9f2e2;
        }
        .bg-blob.sky {
          width: 280px;
          height: 280px;
          bottom: 0;
          left: 35%;
          background: #cfe7ff;
        }

        .container {
          max-width: 880px;
          margin: 0 auto;
        }

        .hero .eyebrow {
          font-size: 12px;
          letter-spacing: 0.3em;
          color: #6b6b6b;
        }
        .hero h1 {
          margin: 8px 0 0;
          font-size: 30px;
          font-weight: 600;
        }
        .hero .sub {
          margin-top: 10px;
          font-size: 14px;
          color: #6b6b6b;
        }

        .chat-card {
          margin-top: 22px;
          border: 1px solid rgba(0, 0, 0, 0.06);
          background: rgba(255, 255, 255, 0.78);
          border-radius: 28px;
          box-shadow: 0 12px 40px rgba(0, 0, 0, 0.08);
          backdrop-filter: blur(20px);
        }
        .chat-title {
          padding: 18px 24px 0;
          font-size: 11px;
          letter-spacing: 0.2em;
          color: #777;
          text-transform: uppercase;
        }
        .chat-body {
          height: 60vh;
          overflow-y: auto;
          padding: 16px 24px 32px;
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .msg {
          display: flex;
        }
        .msg.right {
          justify-content: flex-end;
        }
        .bubble {
          max-width: 85%;
          padding: 10px 14px;
          font-size: 14px;
          line-height: 1.5;
          border-radius: 18px;
          white-space: pre-wrap;
        }
        .bubble.user {
          background: #111;
          color: #fff;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
        }
        .bubble.assistant {
          background: rgba(255, 255, 255, 0.9);
          border: 1px solid rgba(0, 0, 0, 0.05);
          color: #111;
        }
        .media {
          margin-top: 10px;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .media img,
        .media video {
          width: min(480px, 100%);
          border-radius: 14px;
          border: 1px solid rgba(0, 0, 0, 0.08);
          background: #fff;
        }
        .media-caption {
          font-size: 12px;
          color: #666;
          word-break: break-all;
        }

        a {
          color: #047857;
          text-decoration: underline;
          text-decoration-color: rgba(4, 120, 87, 0.4);
          text-underline-offset: 4px;
        }

        .status {
          font-size: 12px;
          color: #7b7b7b;
        }

        .composer-wrap {
          position: fixed;
          left: 50%;
          bottom: 24px;
          transform: translateX(-50%);
          width: min(900px, 92vw);
        }
        .composer {
          display: flex;
          align-items: center;
          gap: 16px;
          background: rgba(255, 255, 255, 0.95);
          border: 1px solid rgba(0, 0, 0, 0.08);
          border-radius: 999px;
          padding: 12px 18px;
          box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12);
          backdrop-filter: blur(16px);
        }
        .composer-input {
          flex: 1;
          border: none;
          background: transparent;
          font-size: 16px;
          outline: none;
          color: #111;
        }
        .composer-input::placeholder {
          color: #9a9a9a;
        }
        .icon-btn {
          width: 46px;
          height: 46px;
          border-radius: 50%;
          border: 1px solid rgba(0, 0, 0, 0.12);
          background: #fff;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          color: #111;
        }
        .send-btn {
          width: 46px;
          height: 46px;
          border-radius: 50%;
          border: none;
          background: #111;
          color: #fff;
          display: inline-flex;
          align-items: center;
          justify-content: center;
        }
        .send-btn:disabled {
          opacity: 0.4;
        }

        @media (max-width: 640px) {
          .chat-body {
            height: 56vh;
          }
          .composer {
            gap: 10px;
            padding: 10px 14px;
          }
          .icon-btn,
          .send-btn {
            width: 40px;
            height: 40px;
          }
        }
      `}</style>
    </main>
  );
}
