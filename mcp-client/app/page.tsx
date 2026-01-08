"use client";

import { useMemo, useState } from "react";

type Msg = { role: "user" | "assistant"; content: string };

const URL_RE = /(https?:\/\/[^\s]+)/;
const URL_SPLIT_RE = /(https?:\/\/[^\s]+)/g;

function renderWithLinks(text: string) {
  const parts = text.split(URL_SPLIT_RE);
  return parts.map((part, i) =>
    URL_RE.test(part) ? (
      <a
        key={`url-${i}`}
        href={part}
        target="_blank"
        rel="noreferrer"
        className="underline text-blue-600"
      >
        {part}
      </a>
    ) : (
      <span key={`txt-${i}`}>{part}</span>
    )
  );
}

export default function Home() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: "assistant",
      content:
        "こんにちは。写真取り込みのMCPツールが使えます。例: 「C:\\Users\\J0115990\\Desktop\\NodeScripts\\photoviewer\\samplephotos を dry-run で取り込んで」",
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

      const raw = await r.text(); // まず text で受ける
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
    <main className="min-h-screen p-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">MCP × Gemini Chat Demo</h1>

      <div className="border rounded-xl p-4 h-[65vh] overflow-y-auto space-y-3 bg-white">
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
            <div
              className={[
                "inline-block px-3 py-2 rounded-2xl max-w-[85%] whitespace-pre-wrap",
                m.role === "user" ? "bg-gray-200" : "bg-gray-100",
              ].join(" ")}
            >
              {renderWithLinks(m.content)}
            </div>
          </div>
        ))}
        {busy && <div className="text-sm text-gray-500">ツール実行中 / 生成中…</div>}
      </div>

      <div className="mt-4 flex gap-2">
        <input
          className="flex-1 border rounded-xl px-3 py-2"
          placeholder="例：C:\\photos を dry-run で取り込んで"
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
          className="px-4 py-2 rounded-xl bg-black text-white disabled:opacity-40"
          onClick={send}
          disabled={!canSend}
        >
          送信
        </button>
      </div>

      <p className="mt-3 text-sm text-gray-600">
        ※ Gemini は必要に応じて MCP ツールを自動で呼びます（mcpToTool）。
      </p>
    </main>
  );
}
