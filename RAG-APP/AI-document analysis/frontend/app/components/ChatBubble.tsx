import { Bot, User } from "lucide-react";
import { Message } from "../types";
import { FormattedMessage } from "./FormattedMessage";
import { TypewriterMessage } from "./TypewriterMessage";
import { SourcesDropdown } from "./SourcesDropdown";

export function ChatBubble({ message, isLatest }: { message: Message, isLatest: boolean }) {
    const isUser = message.role === "user";
    const answerSource = message.answer_source;

    return (
        <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
            <div
                className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 border shadow-sm ${isUser
                        ? "bg-blue-600 border-blue-500 text-white"
                        : "bg-white dark:bg-zinc-900 border-gray-100 dark:border-zinc-800 text-blue-600 dark:text-blue-400"
                    }`}
            >
                {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
            </div>

            <div className={`max-w-[85%] flex flex-col ${isUser ? "items-end" : ""}`}>
                {/* Source badge */}
                {!isUser && answerSource && (
                    <div className="mb-1">
                        {answerSource === "document" ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400 border border-green-200 dark:border-green-800">
                                📄 From Documents
                            </span>
                        ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 border border-purple-200 dark:border-purple-800">
                                🤖 From LLM Knowledge
                            </span>
                        )}
                    </div>
                )}

                <div
                    className={`px-4 py-3 rounded-2xl shadow-sm ${isUser
                            ? "bg-blue-600 text-white rounded-tr-none border border-blue-500"
                            : "bg-white dark:bg-zinc-900 text-gray-800 dark:text-zinc-200 rounded-tl-none border border-gray-100 dark:border-zinc-800"
                        }`}
                >
                    {isLatest && !isUser && !message.content ? (
                        <TypewriterMessage content="..." />
                    ) : (
                        <FormattedMessage content={message.content} isUser={isUser} />
                    )}

                    {!isUser && message.sources && message.sources.length > 0 && (
                        <SourcesDropdown sources={message.sources} />
                    )}
                </div>
                <div className="mt-1 px-1 text-[10px] text-gray-400 dark:text-zinc-500 font-medium">
                    {message.ts}
                </div>
            </div>
        </div>
    );
}
