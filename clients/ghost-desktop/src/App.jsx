import { useEffect, useState } from "react";
import ChatInterface from "./pages/ChatInterface";
import Launcher from "./pages/Launcher";

export default function App() {
  const [isReady, setIsReady] = useState(false);
  
  useEffect(() => {
    // Check if we're in the launcher window
    console.log("App mounted, pathname:", globalThis.location.pathname);
    setIsReady(true);
  }, []);

  if (!isReady) {
    return <div className="min-h-screen bg-black flex items-center justify-center text-white">Loading...</div>;
  }

  // Determine which interface to show based on window label
  const isLauncher = globalThis.location.pathname === '/launcher.html';
  
  console.log("Rendering:", isLauncher ? "Launcher" : "ChatInterface");
  
  return isLauncher ? <Launcher /> : <ChatInterface />;
}