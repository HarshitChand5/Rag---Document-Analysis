export type AppMode = "chat" | "upload" | "library" | "export";

export interface Source {
    id: string;
    type: string;
    title?: string;
    pdf_url?: string;
    page?: number;
    metadata?: {
        page?: number;
        page_number?: number;
        [key: string]: any;
    };
    page_number?: number;
}

export interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    ts: string;
    sources?: Source[];
    answer_source?: "document" | "llm";
}

export interface LibraryItem {
    id: string;
    doc_id?: string;
    title: string;
    type: "pdf" | "docx" | "txt";
    date: string;
    url?: string;
    s3_key?: string;
    status?: "processing" | "ready" | "error";
}
