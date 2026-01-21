import { useEffect, useState } from "react";
import ChatInterface from "./pages/ChatInterface";
import Launcher from "./pages/Launcher";

export default function App() {
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    setIsReady(true);
  }, []);

  if (!isReady) {
    return (
      <div className="min-h-screen bg-identra-bg flex items-center justify-center text-identra-text-secondary">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-identra-surface-elevated border border-identra-border-subtle flex items-center justify-center transition-all duration-150">
            <div className="w-5 h-5 rounded-full bg-identra-surface" />
          </div>
          <p className="text-xs tracking-[0.18em] uppercase">Loading Identra</p>
        </div>
      </div>
    );
  }

  const isLauncher = globalThis.location.pathname === "/launcher.html";

  return isLauncher ? <Launcher /> : <ChatInterface />;
}