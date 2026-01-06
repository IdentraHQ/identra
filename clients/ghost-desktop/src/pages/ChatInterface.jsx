import { useState, useEffect, useRef } from "react";
import { 
  Send, 
  Plus, 
  Settings, 
  User, 
  Shield, 
  Database,
  Cpu,
  Lock,
  Menu,
  X,
  Command
} from "lucide-react";
import { invoke } from "@tauri-apps/api/core";

export default function ChatInterface() {
  console.log("ChatInterface rendering");
  
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: "assistant",
      content: "Hello! I'm Identra, your confidential AI assistant. All your data stays local and encrypted. How can I help you today?",
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [status, setStatus] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    // Fetch system status
    invoke("get_system_status")
      .then(setStatus)
      .catch(err => console.error("Failed to get status:", err));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isProcessing) return;

    const userMessage = {
      id: Date.now(),
      role: "user",
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setIsProcessing(true);

    try {
      const response = await invoke("vault_memory", { content: input });
      
      const assistantMessage = {
        id: Date.now() + 1,
        role: "assistant",
        content: response,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      console.error("Error:", err);
      const errorMessage = {
        id: Date.now() + 1,
        role: "assistant",
        content: `Error: ${err}`,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-screen bg-black text-identra-text-primary">
      
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? 'w-64' : 'w-0'} transition-all duration-300 bg-identra-surface border-r border-identra-border overflow-hidden flex flex-col`}>
        <div className="p-4 border-b border-identra-border">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-lg font-semibold flex items-center gap-2">
              <Shield className="w-5 h-5 text-identra-accent" />
              Identra OS
            </h1>
            <button 
              onClick={() => setSidebarOpen(false)}
              className="p-1 hover:bg-identra-bg rounded"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <button className="w-full flex items-center gap-2 px-3 py-2 bg-identra-accent/10 hover:bg-identra-accent/20 border border-identra-accent/30 rounded-lg text-sm font-medium transition-colors">
            <Plus className="w-4 h-4" />
            New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          <div className="text-xs text-identra-text-muted uppercase tracking-wider px-3 py-2 font-semibold">
            Recent Chats
          </div>
          {/* Chat history will go here */}
          <div className="space-y-1">
            <div className="px-3 py-2 rounded hover:bg-identra-bg cursor-pointer text-sm">
              Previous conversation...
            </div>
          </div>
        </div>

        <div className="p-3 border-t border-identra-border space-y-2">
          <button className="w-full flex items-center gap-2 px-3 py-2 hover:bg-identra-bg rounded text-sm">
            <Settings className="w-4 h-4" />
            Settings
          </button>
          <div className="px-3 py-2 bg-identra-bg/50 rounded text-xs space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-identra-text-muted">Status</span>
              <span className="text-identra-accent">{status?.vault_status || "LOCKED"}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-identra-text-muted">Identity</span>
              <span className="text-identra-text-secondary text-[10px]">{status?.active_identity || "None"}</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col">
        
        {/* Top Bar */}
        <header className="h-14 border-b border-identra-border flex items-center justify-between px-4 bg-identra-surface/50">
          <div className="flex items-center gap-3">
            {!sidebarOpen && (
              <button 
                onClick={() => setSidebarOpen(true)}
                className="p-2 hover:bg-identra-bg rounded"
              >
                <Menu className="w-5 h-5" />
              </button>
            )}
            <h2 className="font-medium">Confidential AI Chat</h2>
          </div>
          
          <div className="flex items-center gap-4 text-xs">
            <button
              onClick={() => invoke("toggle_launcher")}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-identra-accent/10 hover:bg-identra-accent/20 border border-identra-accent/30 rounded-lg text-identra-accent transition-colors"
            >
              <Command className="w-3.5 h-3.5" />
              <span>Quick Launcher (Alt+Space)</span>
            </button>
            <div className="flex items-center gap-1.5 text-identra-text-secondary">
              <Cpu className="w-3.5 h-3.5" />
              <span>{status?.enclave_connection ? "Enclave Active" : "Offline"}</span>
            </div>
            <div className="flex items-center gap-1.5 text-identra-text-secondary">
              <Database className="w-3.5 h-3.5" />
              <span>Local Memory</span>
            </div>
          </div>
        </header>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.map((msg) => (
              <div 
                key={msg.id} 
                className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : ''}`}
              >
                {msg.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-full bg-identra-accent/20 flex items-center justify-center shrink-0">
                    <Shield className="w-4 h-4 text-identra-accent" />
                  </div>
                )}
                <div className={`flex flex-col gap-1 ${msg.role === 'user' ? 'items-end' : ''}`}>
                  <div className={`px-4 py-3 rounded-2xl ${
                    msg.role === 'user' 
                      ? 'bg-identra-accent text-white' 
                      : 'bg-identra-surface border border-identra-border'
                  }`}>
                    <p className="text-sm leading-relaxed">{msg.content}</p>
                  </div>
                  <span className="text-[10px] text-identra-text-muted px-2">
                    {msg.timestamp.toLocaleTimeString()}
                  </span>
                </div>
                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-full bg-identra-border flex items-center justify-center shrink-0">
                    <User className="w-4 h-4 text-identra-text-secondary" />
                  </div>
                )}
              </div>
            ))}
            {isProcessing && (
              <div className="flex gap-4">
                <div className="w-8 h-8 rounded-full bg-identra-accent/20 flex items-center justify-center shrink-0">
                  <Shield className="w-4 h-4 text-identra-accent animate-pulse" />
                </div>
                <div className="px-4 py-3 rounded-2xl bg-identra-surface border border-identra-border">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-identra-text-muted rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                    <span className="w-2 h-2 bg-identra-text-muted rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                    <span className="w-2 h-2 bg-identra-text-muted rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Area */}
        <div className="border-t border-identra-border p-4 bg-identra-surface/30">
          <div className="max-w-3xl mx-auto">
            <div className="flex items-end gap-3 bg-identra-surface border border-identra-border rounded-2xl p-3">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask Identra anything... (Shift+Enter for new line)"
                className="flex-1 bg-transparent text-sm resize-none outline-none max-h-32 min-h-[24px]"
                rows={1}
                disabled={isProcessing}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isProcessing}
                className="p-2 bg-identra-accent hover:bg-identra-accent/80 disabled:bg-identra-border disabled:cursor-not-allowed rounded-xl transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
            <div className="flex items-center justify-center gap-2 mt-2 text-[10px] text-identra-text-muted">
              <Lock className="w-3 h-3" />
              <span>All data encrypted locally • Zero-knowledge architecture</span>
            </div>
          </div>
        </div>

      </main>
    </div>
  );
}
