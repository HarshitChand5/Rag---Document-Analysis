import { useState, useMemo } from "react";
import { Copy, Code2 } from "lucide-react";
import { Message } from "../types";

export function QAExportPanel({ messages }: { messages: Message[] }) {
    const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
    const [copiedAll, setCopiedAll] = useState(false);

    const qaPairs = useMemo(() => {
        const pairs: { question: string; answer: string; source: string }[] = [];
        for (let i = 0; i < messages.length; i++) {
            if (messages[i].role === "user") {
                const next = messages[i + 1];
                if (next && next.role === "assistant") {
                    pairs.push({
                        question: messages[i].content,
                        answer: next.content,
                        source: next.answer_source === "llm" ? "LLM Knowledge" : "Documents",
                    });
                }
            }
        }
        return pairs;
    }, [messages]);

    function generateHTML(pair: { question: string; answer: string; source: string }) {
        const sourceTag =
            pair.source === "LLM Knowledge"
                ? `<span style="background:#f3e8ff;color:#7c3aed;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;">🤖 LLM Knowledge</span>`
                : `<span style="background:#ecfdf5;color:#059669;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;">📄 Documents</span>`;

        const answerHtml = pair.answer
            .split("\n")
            .map((line) => {
                const trimmed = line.trim();
                if (!trimmed) return "";
                if (trimmed.startsWith("- ") || trimmed.startsWith("* "))
                    return `<li>${trimmed.slice(2)}</li>`;
                return `<p>${trimmed}</p>`;
            })
            .join("\n");

        const finalAnswer = answerHtml.includes("<li>")
            ? answerHtml.replace(
                /(<li>.*<\/li>\n?)+/g,
                (match) => `<ul style="margin:8px 0;padding-left:20px;">${match}</ul>`
            )
            : answerHtml;

        return `<div style="border:1px solid #e5e7eb;border-radius:12px;padding:16px;margin-bottom:16px;font-family:system-ui,-apple-system,sans-serif;">
  <div style="margin-bottom:12px;">${sourceTag}</div>
  <div style="margin-bottom:12px;">
    <strong style="color:#1f2937;font-size:14px;">Q: ${pair.question}</strong>
  </div>
  <div style="color:#374151;font-size:13px;line-height:1.6;">
    ${finalAnswer}
  </div>
</div>`;
    }

    const copyToClipboard = (text: string, idx?: number) => {
        navigator.clipboard.writeText(text).then(() => {
            if (idx !== undefined) {
                setCopiedIdx(idx);
                setTimeout(() => setCopiedIdx(null), 2000);
            } else {
                setCopiedAll(true);
                setTimeout(() => setCopiedAll(false), 2000);
            }
        });
    };

    const copyAll = () => {
        const allHtml = qaPairs.map((p) => generateHTML(p)).join("\n");
        const wrapped = `<div style="max-width:800px;margin:0 auto;padding:20px;">
  <h2 style="color:#111827;font-size:20px;margin-bottom:24px;border-bottom:2px solid #3b82f6;padding-bottom:8px;">Research Q&A Export</h2>
  ${allHtml}
</div>`;
        copyToClipboard(wrapped);
    };

    if (qaPairs.length === 0) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-gray-50/50 dark:bg-zinc-900/30 rounded-xl border border-dashed border-gray-200 dark:border-zinc-800 m-4">
                <div className="w-12 h-12 rounded-full bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center text-blue-600 dark:text-blue-400 mb-3">
                    <Code2 className="h-6 w-6" />
                </div>
                <p className="text-sm font-medium text-gray-900 dark:text-zinc-100 italic">No Q&A pairs to export yet.</p>
                <p className="text-xs text-gray-500 dark:text-zinc-500 mt-1">Start a conversation to see pairs here.</p>
            </div>
        );
    }

    return (
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {/* Copy All button */}
            <button
                onClick={copyAll}
                className={`w-full flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-medium transition-all ${copiedAll
                        ? "bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 border border-green-200 dark:border-green-800"
                        : "bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800 hover:bg-blue-100 dark:hover:bg-blue-900/40"
                    }`}
            >
                <Copy className="h-3.5 w-3.5" />
                {copiedAll ? "Copied All!" : `Copy All (${qaPairs.length} pairs)`}
            </button>

            <div className="space-y-3 overflow-y-auto">
                {qaPairs.map((pair, idx) => (
                    <div
                        key={idx}
                        className="group relative p-3 rounded-xl bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 hover:border-blue-300 dark:hover:border-blue-900 transition-all shadow-sm"
                    >
                        <div className="flex items-start justify-between gap-3 mb-2">
                            <span
                                className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${pair.source === "LLM Knowledge"
                                        ? "bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400"
                                        : "bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400"
                                    }`}
                            >
                                {pair.source === "LLM Knowledge" ? "🤖 LLM" : "📄 DOC"}
                            </span>
                            <button
                                onClick={() => copyToClipboard(generateHTML(pair), idx)}
                                className="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-zinc-800 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                                title="Copy single HTML snippet"
                            >
                                {copiedIdx === idx ? <div className="text-[10px] font-bold text-green-600">COPIED</div> : <Copy className="h-3.5 w-3.5" />}
                            </button>
                        </div>
                        <p className="text-[12px] font-bold text-gray-800 dark:text-zinc-200 line-clamp-2 mb-1.5">Q: {pair.question}</p>
                        <p className="text-[11px] text-gray-500 dark:text-zinc-500 line-clamp-3 leading-relaxed">{pair.answer}</p>
                    </div>
                ))}
            </div>
        </div>
    );
}
