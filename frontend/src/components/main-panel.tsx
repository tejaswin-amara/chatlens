const messages = [
  {
    role: "assistant",
    content:
      "Welcome to ChatLens v1.0. Select a conversation from the sidebar to inspect summaries, sentiment, and topics.",
  },
  {
    role: "user",
    content: "Give me a quick pulse on the Product Team chat.",
  },
  {
    role: "assistant",
    content:
      "Recent tone is positive. Main themes: release timeline, launch blockers, and customer onboarding updates.",
  },
];

export function MainPanel() {
  return (
    <main className="glass-panel flex h-[calc(100vh-2rem)] min-w-0 flex-1 flex-col border-white/12">
      <header className="flex items-center justify-between border-b border-white/10 px-6 py-4">
        <div>
          <h2 className="text-base font-semibold text-white">Product Team</h2>
          <p className="text-xs text-white/55">Last active 12m ago</p>
        </div>
        <div className="flex gap-2">
          <button className="glass-button" type="button">
            Summarize
          </button>
          <button className="glass-button" type="button">
            Full Analysis
          </button>
        </div>
      </header>

      <section className="flex-1 space-y-3 overflow-y-auto px-6 py-6">
        {messages.map((message, index) => (
          <article
            key={`${message.role}-${index}`}
            className={`max-w-3xl rounded-2xl border px-4 py-3 ${
              message.role === "assistant"
                ? "border-white/15 bg-white/7 text-white"
                : "ml-auto border-cyan-300/30 bg-cyan-300/12 text-cyan-50"
            }`}
          >
            <p className="text-sm leading-6">{message.content}</p>
          </article>
        ))}
      </section>

      <footer className="border-t border-white/10 px-6 py-4">
        <div className="flex items-center gap-3 rounded-xl border border-white/12 bg-white/4 p-2">
          <input
            className="flex-1 bg-transparent px-2 py-2 text-sm text-white placeholder:text-white/45 focus:outline-none"
            placeholder="Ask across your conversations…"
            type="text"
          />
          <button className="glass-button !bg-cyan-300/80 !text-slate-950" type="button">
            Send
          </button>
        </div>
      </footer>
    </main>
  );
}
