import { UploadCloud, Library, Code2, Trash2, FileText, Loader2 } from "lucide-react";
import { AppMode, LibraryItem } from "../types";
import { QAExportPanel } from "./QAExportPanel";
import { Message } from "../types";

interface SidebarProps {
    sidebarTab: AppMode;
    setSidebarTab: (tab: AppMode) => void;
    library: LibraryItem[];
    isLoadingLibrary: boolean;
    docStats: any;
    messages: Message[];
    handleFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
    handleDeleteLibraryItem: (item: LibraryItem) => void;
    handleDownloadItem: (item: LibraryItem) => void;
}

export function Sidebar({
    sidebarTab,
    setSidebarTab,
    library,
    isLoadingLibrary,
    docStats,
    messages,
    handleFileChange,
    handleDeleteLibraryItem,
    handleDownloadItem,
}: SidebarProps) {
    return (
        <aside className="w-[320px] border-r border-gray-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-950/80 backdrop-blur-xl flex flex-col h-full overflow-hidden">
            {/* Sidebar Tabs */}
            <div className="flex border-b border-gray-200 dark:border-zinc-800 px-2 pt-2 bg-gray-50/50 dark:bg-zinc-900/50">
                <button
                    onClick={() => setSidebarTab("upload")}
                    className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium transition-all border-b-2 -mb-px ${sidebarTab === "upload"
                        ? "border-blue-600 text-blue-600"
                        : "border-transparent text-gray-500 dark:text-zinc-500 hover:text-gray-700 dark:hover:text-zinc-300"
                        }`}
                >
                    <UploadCloud className="h-3.5 w-3.5" /> Upload
                </button>
                <button
                    onClick={() => setSidebarTab("library")}
                    className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium transition-all border-b-2 -mb-px ${sidebarTab === "library"
                        ? "border-blue-600 text-blue-600"
                        : "border-transparent text-gray-500 dark:text-zinc-500 hover:text-gray-700 dark:hover:text-zinc-300"
                        }`}
                >
                    <Library className="h-3.5 w-3.5" /> My Library
                    {library.length > 0 && (
                        <span className="ml-1 px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 leading-none">
                            {library.length}
                        </span>
                    )}
                </button>
                <button
                    onClick={() => setSidebarTab("export")}
                    className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium transition-all border-b-2 -mb-px ${sidebarTab === "export"
                        ? "border-blue-600 text-blue-600"
                        : "border-transparent text-gray-500 dark:text-zinc-500 hover:text-gray-700 dark:hover:text-zinc-300"
                        }`}
                >
                    <Code2 className="h-3.5 w-3.5" /> Export
                </button>
            </div>

            <div className="flex-1 overflow-y-auto flex flex-col min-h-0">
                {sidebarTab === "upload" ? (
                    /* Content: Upload */
                    <div className="p-6 space-y-6">
                        <div className="space-y-2">
                            <h3 className="text-sm font-semibold text-gray-900 dark:text-zinc-100">Quick Upload</h3>
                            <p className="text-xs text-gray-500 dark:text-zinc-500">
                                Upload business docs, research papers, or TXT files to analyze them.
                            </p>
                        </div>

                        <div className="relative group">
                            <input
                                type="file"
                                onChange={handleFileChange}
                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                                accept=".pdf,.docx,.txt"
                            />
                            <div className="h-36 rounded-2xl border-2 border-dashed border-gray-200 dark:border-zinc-800 flex flex-col items-center justify-center gap-3 bg-white dark:bg-zinc-900 group-hover:border-blue-500/50 group-hover:bg-blue-50/30 dark:group-hover:bg-blue-900/10 transition-all">
                                <div className="w-12 h-12 rounded-full bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center text-blue-600">
                                    <UploadCloud className="h-6 w-6" />
                                </div>
                                <div className="text-center">
                                    <span className="text-xs font-semibold text-gray-900 dark:text-zinc-100 block">Click or Drop</span>
                                    <span className="text-[10px] text-gray-500 dark:text-zinc-500 block">PDF, DOCX, TXT</span>
                                </div>
                            </div>
                        </div>


                    </div>
                ) : sidebarTab === "library" ? (
                    /* Content: Library */
                    <div className="flex-1 overflow-y-auto p-4 flex flex-col min-h-0">
                        {isLoadingLibrary ? (
                            <div className="flex-1 flex items-center justify-center py-12">
                                <div className="animate-spin rounded-full h-5 w-5 border-2 border-blue-600 border-t-transparent" />
                            </div>
                        ) : library.length > 0 ? (
                            <div className="space-y-2">
                                {library.map((item) => (
                                    <div
                                        key={item.id}
                                        className="p-3 rounded-xl bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 hover:border-blue-300 dark:hover:border-blue-900 transition-all group shadow-sm"
                                    >
                                        <div className="flex items-start gap-3">
                                            <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-600">
                                                <FileText className="h-4 w-4" />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="text-xs font-semibold text-gray-900 dark:text-zinc-100 truncate mb-0.5 flex items-center gap-2">
                                                    {item.title}
                                                    {item.status === "processing" && (
                                                        <Loader2 className="h-3 w-3 animate-spin text-blue-600" />
                                                    )}
                                                </div>
                                                <div className="flex items-center gap-2 text-[10px] text-gray-500 dark:text-zinc-500">
                                                    <span className="capitalize">{item.type}</span>
                                                    <span>•</span>
                                                    <span>{item.date}</span>
                                                    {item.status === "processing" && (
                                                        <>
                                                            <span>•</span>
                                                            <span className="text-blue-600 dark:text-blue-400 font-bold animate-pulse uppercase tracking-tighter">Processing...</span>
                                                        </>
                                                    )}
                                                    {item.status === "error" && (
                                                        <>
                                                            <span>•</span>
                                                            <span className="text-red-500 font-bold uppercase tracking-tighter">Error</span>
                                                        </>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-1 mt-3 pt-3 border-t border-gray-50 dark:border-zinc-800 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <button
                                                onClick={() => handleDownloadItem(item)}
                                                disabled={item.status === "processing"}
                                                className={`text-[10px] px-2.5 py-1 rounded-md border font-medium flex-1 text-center transition-colors ${item.status === "processing"
                                                    ? "bg-gray-50 dark:bg-zinc-800 border-gray-100 dark:border-zinc-700 text-gray-400 cursor-not-allowed"
                                                    : "bg-white dark:bg-zinc-900 border-gray-200 dark:border-zinc-700 text-gray-600 dark:text-zinc-400 hover:bg-gray-50 dark:hover:bg-zinc-800"
                                                    }`}
                                            >
                                                {item.status === "processing" ? "Ingesting..." : "Preview / Download"}
                                            </button>
                                            <button
                                                onClick={() => handleDeleteLibraryItem(item)}
                                                className="p-1 rounded-md text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all"
                                                title="Delete Document"
                                            >
                                                <Trash2 className="h-3.5 w-3.5" />
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
                                <div className="w-12 h-12 rounded-full bg-gray-50 dark:bg-zinc-900 flex items-center justify-center text-gray-400 mb-3">
                                    <Library className="h-6 w-6" />
                                </div>
                                <p className="text-sm font-medium text-gray-900 dark:text-zinc-100 italic">No documents yet.</p>
                                <p className="text-xs text-gray-500 dark:text-zinc-500 mt-1">Upload files to build your knowledge base.</p>
                            </div>
                        )}
                    </div>
                ) : (
                    /* Content: Q&A Export */
                    <QAExportPanel messages={messages} />
                )}
            </div>
        </aside>
    );
}
