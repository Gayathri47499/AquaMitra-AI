import { Fragment } from "react";

// Turns **bold** into bold text.
function inline(text) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") && part.length > 4
      ? <strong key={i} className="font-semibold">{part.slice(2, -2)}</strong>
      : <Fragment key={i}>{part}</Fragment>
  );
}

// Shows an assistant answer with paragraphs, numbered steps and bullets.
export default function AnswerText({ text }) {
  const blocks = [];

  for (const raw of (text || "").split("\n")) {
    const line = raw.trim();
    if (!line) continue;

    const num = line.match(/^\d+\.\s+(.*)$/);
    const bul = line.match(/^[-•]\s+(.*)$/);
    const last = blocks[blocks.length - 1];

    if (num) {
      if (last?.type === "ol") last.items.push(num[1]);
      else blocks.push({ type: "ol", items: [num[1]] });
    } else if (bul) {
      if (last?.type === "ul") last.items.push(bul[1]);
      else blocks.push({ type: "ul", items: [bul[1]] });
    } else {
      blocks.push({ type: "p", text: line });
    }
  }

  return (
    <div className="space-y-3 leading-relaxed">
      {blocks.map((b, i) => {
        if (b.type === "ol")
          return (
            <ol key={i} className="list-decimal space-y-2 pl-6">
              {b.items.map((t, j) => <li key={j}>{inline(t)}</li>)}
            </ol>
          );
        if (b.type === "ul")
          return (
            <ul key={i} className="list-disc space-y-1 pl-6">
              {b.items.map((t, j) => <li key={j}>{inline(t)}</li>)}
            </ul>
          );
        return <p key={i}>{inline(b.text)}</p>;
      })}
    </div>
  );
}