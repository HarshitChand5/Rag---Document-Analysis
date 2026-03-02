import React from "react";

export function FormattedMessage({ content, isUser }: { content: string; isUser: boolean }) {
    const parseLine = (text: string) => {
        // Basic Markdown bullet detection
        if (text.trim().startsWith("- ") || text.trim().startsWith("* ")) {
            return <li className="ml-4 list-disc marker:text-blue-500/50">{text.trim().slice(2)}</li>;
        }
        // Bold text **bold**
        const parts = text.split(/(\*\*.*?\*\*)/g);
        return (
            <p>
                {parts.map((part, i) =>
                    part.startsWith("**") && part.endsWith("**") ? (
                        <strong key={i} className="font-bold text-gray-900 dark:text-zinc-100">
                            {part.slice(2, -2)}
                        </strong>
                    ) : (
                        part
                    )
                )}
            </p>
        );
    };

    const lines = content.split("\n").filter((l) => l.trim() !== "");

    return (
        <div className={`space-y-2 text-[14px] leading-relaxed ${isUser ? "text-white" : "text-gray-700 dark:text-zinc-300"}`}>
            {lines.map((line, idx) => (
                <React.Fragment key={idx}>{parseLine(line)}</React.Fragment>
            ))}
        </div>
    );
}
