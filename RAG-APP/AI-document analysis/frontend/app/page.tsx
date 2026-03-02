"use client";

import { useState, useRef, useEffect } from "react";
import {
  Send,
  Paperclip,
  Moon,
  Sun,
  Trash2,
  Loader2,
  MessageSquare,
} from "lucide-react";

import { Message, AppMode } from "./types";
import { useChat } from "./hooks/useChat";
import { useLibrary } from "./hooks/useLibrary";
import { ChatBubble } from "./components/ChatBubble";
import { Sidebar } from "./components/Sidebar";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
const ENV_DEFAULT_PROJECT_ID = process.env.NEXT_PUBLIC_DEFAULT_PROJECT_ID || "";

export default function HomePage() {
  const [projectId, setProjectId] = useState(ENV_DEFAULT_PROJECT_ID);
  const [inputQuestion, setInputQuestion] = useState("");
  const [sidebarTab, setSidebarTab] = useState<AppMode>("upload");
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [isUploading, setIsUploading] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);

  // Initialize Project ID if empty
  useEffect(() => {
    if (!projectId) {
      const newId = Math.random().toString(36).substring(7);
      setProjectId(newId);
    }
  }, [projectId]);

  // Theme Management
  useEffect(() => {
    const savedTheme = localStorage.getItem("theme") as "light" | "dark";
    if (savedTheme) {
      setTheme(savedTheme);
      document.documentElement.classList.toggle("dark", savedTheme === "dark");
    }
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === "light" ? "dark" : "light";
    setTheme(newTheme);
    localStorage.setItem("theme", newTheme);
    document.documentElement.classList.toggle("dark", newTheme === "dark");
  };

  // Custom Hooks
  const { messages, isTyping, callChatAPI, clearMessages } = useChat(projectId);
  const {
    library,
    isLoadingLibrary,
    docStats,
    fetchLibrary,
    handleDeleteLibraryItem,
    handleDownloadItem
  } = useLibrary(projectId);

  // Initial Library Load
  useEffect(() => {
    if (projectId) fetchLibrary();
  }, [projectId, fetchLibrary]);

  // Auto-scroll chat
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuestion.trim()) return;
    callChatAPI(inputQuestion);
    setInputQuestion("");
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/ingest?project_id=${projectId}`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Upload failed");

      fetchLibrary();
      setSidebarTab("library");
    } catch (err) {
      console.error(err);
      alert("Upload failed. Please try again.");
    } finally {
      setIsUploading(false);
      e.target.value = ""; // Clear input
    }
  };

  const handleNewWorkspace = () => {
    if (confirm("Reset current project? This will clear chat history locally.")) {
      const newId = Math.random().toString(36).substring(7);
      setProjectId(newId);
      clearMessages();
      setSidebarTab("upload");
    }
  };

  return (
    <div className={`flex h-screen bg-gray-50 dark:bg-zinc-950 text-gray-900 dark:text-zinc-100 transition-colors duration-300`}>
      {/* Sidebar Component */}
      <Sidebar
        sidebarTab={sidebarTab}
        setSidebarTab={setSidebarTab}
        library={library}
        isLoadingLibrary={isLoadingLibrary}
        docStats={docStats}
        messages={messages}
        handleFileChange={handleFileChange}
        handleDeleteLibraryItem={handleDeleteLibraryItem}
        handleDownloadItem={handleDownloadItem}
      />

      <main className="flex-1 flex flex-col relative min-w-0">
        {/* Header */}
        <header className="h-16 border-b border-gray-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-950/50 backdrop-blur-xl px-6 flex items-center justify-between z-20">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <span className="text-white font-black italic tracking-tighter">AI</span>
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-tight">Document Researcher</h1>
              <div className="flex items-center gap-1.5 text-[10px] text-gray-500 dark:text-zinc-500 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                Live Workspace
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={toggleTheme}
              className="p-2.5 rounded-xl hover:bg-gray-100 dark:hover:bg-zinc-800 transition-all text-gray-500 dark:text-zinc-400 border border-transparent hover:border-gray-200 dark:hover:border-zinc-700"
            >
              {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
            </button>
            <button
              onClick={handleNewWorkspace}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-gray-100 dark:bg-zinc-900 text-gray-700 dark:text-zinc-300 border border-gray-200 dark:border-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-800 transition-all"
            >
              New Workspace
            </button>
          </div>
        </header>

        {/* Chat Area */}
        <div className="flex-1 relative overflow-hidden flex flex-col bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-blue-50/20 via-transparent to-transparent">
          <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto px-6 py-8 space-y-8 scroll-smooth"
          >
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center space-y-6 text-center max-w-md mx-auto">
                <div className="relative">
                  <div className="absolute inset-0 bg-blue-500/20 blur-3xl rounded-full scale-150 animate-pulse" />
                  <div className="relative w-20 h-20 rounded-3xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-2xl text-white">
                    <MessageSquare size={36} />
                  </div>
                </div>
                <div className="space-y-2 relative">
                  <h2 className="text-2xl font-black tracking-tight text-gray-900 dark:text-zinc-100">Intelligent Research</h2>
                  <p className="text-sm text-gray-500 dark:text-zinc-500 leading-relaxed px-4">
                    Upload your documents to the sidebar, then ask questions. I'll search your papers and use advanced AI to synthesize answers.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 justify-center pt-4">
                  {["Summarize the main points", "Extract key technical data", "Compare results"].map((suggestion) => (
                    <button
                      key={suggestion}
                      onClick={() => setInputQuestion(suggestion)}
                      className="px-3 py-1.5 rounded-lg text-[10px] font-bold bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 hover:border-blue-500 dark:hover:border-blue-500/50 transition-all"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="max-w-4xl mx-auto w-full space-y-8">
                {messages.map((m, idx) => (
                  <ChatBubble
                    key={m.id}
                    message={m}
                    isLatest={idx === messages.length - 1}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Input Bar */}
          <div className="p-6 pt-2 bg-gradient-to-t from-gray-50/80 dark:from-zinc-950/80 to-transparent backdrop-blur-sm">
            <form
              onSubmit={handleSend}
              className="max-w-4xl mx-auto relative group"
            >
              <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl blur opacity-20 group-focus-within:opacity-40 transition-all duration-300" />
              <div className="relative flex items-center bg-white dark:bg-zinc-900 rounded-2xl border border-gray-200 dark:border-zinc-800 shadow-xl overflow-hidden transition-all duration-300 group-focus-within:border-blue-500/50">
                <div className="pl-4 pr-2 text-gray-400">
                  <label htmlFor="chat-upload" className="cursor-pointer">
                    <Paperclip className="h-5 w-5 hover:text-blue-500 transition-colors" />
                    <input
                      id="chat-upload"
                      type="file"
                      className="hidden"
                      onChange={handleFileChange}
                      accept=".pdf,.docx,.txt"
                    />
                  </label>
                </div>
                <input
                  type="text"
                  value={inputQuestion}
                  onChange={(e) => setInputQuestion(e.target.value)}
                  placeholder="Ask your document anything..."
                  className="flex-1 bg-transparent border-none py-4 text-[14px] focus:ring-0 placeholder-gray-400 dark:text-zinc-200"
                />
                <button
                  type="submit"
                  disabled={isTyping || !inputQuestion.trim()}
                  className="mr-2 p-2 rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md active:scale-95"
                >
                  {isTyping ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
                </button>
              </div>
              <div className="mt-3 flex justify-center">
                <p className="text-[10px] font-bold text-gray-400 dark:text-zinc-600 uppercase tracking-widest flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-blue-500/50" />
                  Powered by Gemini 2.0 & LangGraph
                  <span className="w-1 h-1 rounded-full bg-blue-500/50" />
                </p>
              </div>
            </form>
          </div>
        </div>
      </main>

    </div>
  );
}