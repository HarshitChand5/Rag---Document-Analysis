import { useState, useCallback } from "react";
import { Message, Source } from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export function useChat(projectId: string) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [isTyping, setIsTyping] = useState(false);

    const generateMsgId = () => Math.random().toString(36).substring(7);
    const nowLabel = () =>
        new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    const readStream = async (
        response: Response,
        onChunk: (text: string) => void,
        onEvent?: (type: string, data: any) => void
    ) => {
        const reader = response.body?.getReader();
        if (!reader) return;
        const decoder = new TextDecoder();
        let done = false;

        while (!done) {
            const { value, done: doneReading } = await reader.read();
            done = doneReading;
            const chunkValue = decoder.decode(value);
            const lines = chunkValue.split("\n\n");

            for (const line of lines) {
                if (!line.trim()) continue;
                const data = line.replace(/^data: /, "").trim();
                const type = data.startsWith("[SOURCE_TYPE]")
                    ? "SOURCE_TYPE"
                    : data.startsWith("[SOURCES]")
                        ? "SOURCES"
                        : "TEXT";

                if (type === "TEXT") {
                    onChunk(data);
                } else if (type === "SOURCES") {
                    try {
                        const sources = JSON.parse(data.slice(9));
                        if (onEvent) onEvent("SOURCES", sources);
                    } catch (e) { }
                } else if (type === "SOURCE_TYPE") {
                    if (onEvent) onEvent("SOURCE_TYPE", data.slice(13).trim());
                } else if (data.startsWith("[ERROR]")) {
                    onChunk(` Error: ${data.slice(7)}`);
                }
            }
        }
    };

    const callChatAPI = useCallback(async (question: string) => {
        if (!question.trim()) return;

        const userMsg: Message = {
            id: generateMsgId(),
            role: "user",
            content: question,
            ts: nowLabel(),
        };
        const botMsgId = generateMsgId();
        const botMsg: Message = {
            id: botMsgId,
            role: "assistant",
            content: "",
            ts: nowLabel(),
        };

        setMessages((prev) => [...prev, userMsg, botMsg]);
        setIsTyping(true);

        try {
            const resp = await fetch(`${API_BASE}/chat-stream`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ project_id: projectId, question }),
            });

            if (!resp.ok) throw new Error("Stream request failed");

            await readStream(
                resp,
                (chunk) => {
                    setMessages((prev) =>
                        prev.map((m) =>
                            m.id === botMsgId ? { ...m, content: m.content + chunk } : m
                        )
                    );
                },
                (type, data) => {
                    if (type === "SOURCES") {
                        setMessages((prev) =>
                            prev.map((m) => (m.id === botMsgId ? { ...m, sources: data } : m))
                        );
                    } else if (type === "SOURCE_TYPE") {
                        setMessages((prev) =>
                            prev.map((m) =>
                                m.id === botMsgId
                                    ? { ...m, answer_source: data as "document" | "llm" }
                                    : m
                            )
                        );
                    }
                }
            );
        } catch (err) {
            console.error(err);
            setMessages((prev) =>
                prev.map((m) =>
                    m.id === botMsgId
                        ? { ...m, content: "Sorry, I encountered an error. Please try again." }
                        : m
                )
            );
        } finally {
            setIsTyping(false);
        }
    }, [projectId]);

    const clearMessages = () => setMessages([]);

    return {
        messages,
        setMessages,
        isTyping,
        callChatAPI,
        clearMessages,
    };
}
