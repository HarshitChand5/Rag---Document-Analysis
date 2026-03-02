import { useState } from "react";
import { ChevronDown, ChevronUp, FileText } from "lucide-react";
import { Source } from "../types";

export function SourcesDropdown({ sources }: { sources: Source[] }) {
    const [isOpen, setIsOpen] = useState(false);

    if (!sources || sources.length === 0) return null;

    return (
        <div className="mt-3 border-t border-gray-100 dark:border-zinc-800 pt-3">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-1.5 text-[11px] font-semibold text-gray-500 dark:text-zinc-500 hover:text-blue-600 dark:hover:text-blue-400 transition-colors uppercase tracking-wider"
            >
                {isOpen ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                {sources.length} {sources.length === 1 ? "Source" : "Sources"}
            </button>

            {isOpen && (
                <div className="mt-2 space-y-1.5">
                    {sources.map((src, idx) => {
                        const title = src.title || "Document Chunk";
                        const page = src.page || src.metadata?.page || src.metadata?.page_number;

                        return (
                            <div
                                key={idx}
                                className="flex items-center gap-2 p-2 rounded-lg bg-gray-50/80 dark:bg-zinc-800/50 border border-gray-100 dark:border-zinc-800 hover:border-blue-200 dark:hover:border-blue-900/50 transition-all group"
                            >
                                <div className="p-1.5 rounded-md bg-white dark:bg-zinc-900 text-blue-600 dark:text-blue-400 shadow-sm border border-gray-100 dark:border-zinc-800">
                                    <FileText className="h-3 w-3" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="text-[12px] font-medium text-gray-700 dark:text-zinc-300 truncate group-hover:text-blue-600 dark:group-hover:text-blue-400">
                                        {title}
                                    </div>
                                    {page && (
                                        <div className="text-[10px] text-gray-500 dark:text-zinc-500">
                                            Page {page}
                                        </div>
                                    )}
                                </div>
                                {src.pdf_url && (
                                    <a
                                        href={src.pdf_url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="text-[10px] px-2 py-1 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 hover:bg-blue-600 hover:text-white transition-all font-medium"
                                    >
                                        View
                                    </a>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
