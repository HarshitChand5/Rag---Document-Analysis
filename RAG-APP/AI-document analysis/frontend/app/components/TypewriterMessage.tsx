import { useRef, useEffect } from "react";

export function TypewriterMessage({ content }: { content: string }) {
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (containerRef.current) {
            const container = containerRef.current;
            container.scrollTop = container.scrollHeight;
        }
    }, [content]);

    return (
        <div ref={containerRef} className="whitespace-pre-wrap leading-relaxed">
            {content}
            <span className="inline-block w-1.5 h-4 ml-1 bg-current animate-pulse align-middle" />
        </div>
    );
}
