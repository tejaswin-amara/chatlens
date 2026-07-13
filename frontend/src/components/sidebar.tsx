const chats = [
  { name: "Product Team", platform: "Telegram", count: 642, active: true },
  { name: "Family Group", platform: "WhatsApp", count: 231, active: false },
  { name: "Weekend Plans", platform: "Telegram", count: 88, active: false },
];

export function Sidebar() {
  return (
    <aside className="glass-panel hidden h-[calc(100vh-2rem)] w-80 shrink-0 flex-col overflow-hidden border-white/12 md:flex">
      <div className="border-b border-white/10 px-5 py-5">
        <h1 className="text-lg font-semibold tracking-tight text-white">
          ChatLens
        </h1>
        <p className="mt-1 text-xs text-white/60">3 chats indexed • 961 messages</p>
      </div>
      <nav className="space-y-1 overflow-y-auto p-3">
        {chats.map((chat) => (
          <button
            key={chat.name}
            className={`flex w-full items-center justify-between rounded-xl border px-3 py-3 text-left transition ${
              chat.active
                ? "border-cyan-300/35 bg-cyan-300/10"
                : "border-transparent bg-white/2 hover:border-white/15 hover:bg-white/6"
            }`}
            type="button"
          >
            <div>
              <p className="text-sm font-medium text-white">{chat.name}</p>
              <p className="text-xs text-white/50">{chat.count} messages</p>
            </div>
            <span className="rounded-full border border-white/15 bg-white/6 px-2 py-1 text-[10px] font-medium uppercase tracking-wide text-white/75">
              {chat.platform}
            </span>
          </button>
        ))}
      </nav>
    </aside>
  );
}
