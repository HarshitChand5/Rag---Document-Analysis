import { useState, useCallback } from "react";
import { LibraryItem } from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export function useLibrary(projectId: string) {
    const [library, setLibrary] = useState<LibraryItem[]>([]);
    const [isLoadingLibrary, setIsLoadingLibrary] = useState(false);
    const [docStats, setDocStats] = useState<{ total_documents: number; total_chunks: number; last_upload: string | null }>({
        total_documents: 0,
        total_chunks: 0,
        last_upload: null,
    });

    const fetchLibrary = useCallback(async () => {
        if (!projectId) return;
        setIsLoadingLibrary(true);
        try {
            const res = await fetch(`${API_BASE}/documents/${projectId}`);
            const data = await res.json();
            if (data.documents) {
                const mappedDocs: LibraryItem[] = data.documents.map((d: any) => ({
                    id: d.id,
                    doc_id: d.id,
                    title: d.original_filename || d.filename,
                    type: (d.mime_type?.split("/")[1] || "pdf") as any,
                    date: new Date(d.created_at).toLocaleDateString(),
                    s3_key: d.s3_key,
                    status: d.status,
                }));
                setLibrary(mappedDocs);

                // Polling logic: if any item is "processing", refresh in 5 seconds
                const hasProcessing = mappedDocs.some(d => d.status === "processing");
                if (hasProcessing) {
                    setTimeout(fetchLibrary, 5000);
                }
            }

            const statsRes = await fetch(`${API_BASE}/documents/${projectId}/stats`);
            const statsData = await statsRes.json();
            setDocStats({
                total_documents: statsData.total_documents || 0,
                total_chunks: statsData.total_chunks || 0,
                last_upload: statsData.last_upload,
            });
        } catch (err) {
            console.error("Failed to fetch library:", err);
        } finally {
            setIsLoadingLibrary(false);
        }
    }, [projectId]);

    const handleDeleteLibraryItem = async (item: LibraryItem) => {
        if (!confirm(`Are you sure you want to delete "${item.title}"?`)) return;
        try {
            const res = await fetch(`${API_BASE}/documents/${item.id}`, { method: "DELETE" });
            if (res.ok) {
                setLibrary((prev) => prev.filter((i) => i.id !== item.id));
                fetchLibrary(); // Refresh stats
            }
        } catch (err) {
            console.error("Delete failed:", err);
            alert("Failed to delete document.");
        }
    };

    const handleDownloadItem = async (item: LibraryItem) => {
        try {
            const res = await fetch(`${API_BASE}/documents/download/${item.id}`);
            const data = await res.json();
            if (data.url) {
                window.open(data.url, "_blank");
            }
        } catch (err) {
            console.error("Download failed:", err);
        }
    };

    return {
        library,
        isLoadingLibrary,
        docStats,
        fetchLibrary,
        handleDeleteLibraryItem,
        handleDownloadItem,
    };
}
