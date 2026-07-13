import { MainPanel } from "@/components/main-panel";
import { Sidebar } from "@/components/sidebar";

export default function Home() {
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-1 gap-4 px-4 py-4 md:px-6 lg:px-8">
      <Sidebar />
      <MainPanel />
    </div>
  );
}
