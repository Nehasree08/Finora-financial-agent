'use client';
import { FormEvent, useState } from 'react';
import { Bot, Send, X } from 'lucide-react';

export default function AuditChat({ reviewId }: { reviewId?: number }) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<string[]>([]);

  function submit(event: FormEvent) {
    event.preventDefault();
    const question = input.trim();
    if (!question) return;
    setMessages(current => [...current, `You: ${question}`, `Review assistant: I can help inspect validation, variance, ratios, anomalies, and evidence${reviewId ? ` for review #${reviewId}` : ''}. Open the relevant audit layer for the detailed result.`]);
    setInput('');
  }

  return <>
    {open && <section className="audit-chat"><div className="audit-chat-head"><div><Bot size={17}/><b>Review assistant</b></div><button className="icon-btn" onClick={() => setOpen(false)} title="Close chat"><X size={16}/></button></div><div className="audit-chat-body">{messages.length === 0 ? <p>Ask about validation, variance, ratios, anomalies, or review evidence.</p> : messages.map((message, index) => <p key={`${message}-${index}`}>{message}</p>)}</div><form onSubmit={submit}><input value={input} onChange={event => setInput(event.target.value)} placeholder="Ask about this review..."/><button className="icon-btn" type="submit" title="Send"><Send size={16}/></button></form></section>}
    {!open && <button className="chat-launcher" onClick={() => setOpen(true)} title="Open review assistant"><Bot size={18}/><span>Chat</span></button>}
  </>;
}