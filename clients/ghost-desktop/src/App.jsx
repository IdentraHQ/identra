import { useEffect, useState } from "react";
import ChatInterface from "./pages/ChatInterface";
import Launcher from "./pages/Launcher";

export default function App() {
  const [isReady, setIsReady] = useState(false);
  
  useEffect(() => {
    console.log("App mounted, pathname:", globalThis.location.pathname);
    setIsReady(true);
  }, []);

  if (!isReady) {
    return (
      <div className="min-h-screen bg-identra-bg flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-identra-primary to-identra-secondary flex items-center justify-center animate-pulse-subtle">
            <div className="w-6 h-6 rounded-full bg-white/25"></div>
          </div>
          <p className="text-sm text-identra-text-tertiary">Loading Identra...</p>
        </div>
      </div>
    );
  }

  const isLauncher = globalThis.location.pathname === '/launcher.html';
  
  console.log("Rendering:", isLauncher ? "Launcher" : "ChatInterface");
  
  return isLauncher ? <Launcher /> : <ChatInterface />;
}