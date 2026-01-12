import { NextResponse } from "next/server";
import { GoogleGenAI, mcpToTool } from "@google/genai";
import { getMcpClient } from "@/lib/mcpClient";

type Msg = { role: "user" | "assistant"; content: string };

export const runtime = "nodejs";

export async function POST(req: Request) {
  try {
    const { messages, deviceId } = (await req.json()) as {
      messages: Msg[];
      deviceId?: string;
    };

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      return NextResponse.json({ error: "Missing GEMINI_API_KEY" }, { status: 500 });
    }

    const ai = new GoogleGenAI({ apiKey });

    const mcpClient = await getMcpClient(deviceId);

    const contents = messages.map((m) => ({
      role: m.role === "assistant" ? "model" : "user",
      parts: [{ text: m.content }],
    }));

    const resp = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents,
      config: {
        temperature: 0.2,
        tools: [mcpToTool(mcpClient as any)],
        systemInstruction:
          "When a tool response includes viewer_url, reply with that URL explicitly. When a tool response includes media_path, reply with a single [[media]]...[[/media]] block that contains JSON with keys: path, type, mime, name. Do not include the file path outside the media block. root_path means a virtual Firestore path (e.g. 'samplephotos' or '/2024/Trip'), not a local filesystem path. Never ask for absolute local paths for root_path; explain it if the user is confused.",
        // automaticFunctionCalling: { disable: true },
      },
    });

    return NextResponse.json({ text: (resp.text ?? "").trim() });
  } catch (e: any) {
    return NextResponse.json(
      { error: e?.message ?? String(e) },
      { status: 500 }
    );
  }
}
