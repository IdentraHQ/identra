import { useState, useEffect, useRef } from "react";
import { 
  Send, 
  Clock,
  Search,
  MoreVertical,
  Circle,
  FileText,
  ChevronDown,
  Sparkles
} from "lucide-react";
import { invoke } from "@tauri-apps/api/core";

export default function ChatInterface() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [status, setStatus] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [contextPanelOpen, setContextPanelOpen] = useState(true);
  const [selectedModel, setSelectedModel] = useState("claude"); // claude, gemini, gpt
  const [sessionInitialized, setSessionInitialized] = useState(false);
  const [conversationHistory, setConversationHistory] = useState([]);
  const messagesEndRef = useRef(null);

  const models = [
    { id: "claude", name: "Claude 3.5 Sonnet", color: "identra-claude", icon: "⚡" },
    { id: "gemini", name: "Gemini 1.5 Pro", color: "identra-gemini", icon: "✦" },
    { id: "gpt", name: "GPT-4o", color: "identra-gpt", icon: "◆" }
  ];

  const contextDocuments = [
    { id: 1, name: "Auth_Specs_v2.pdf", model: "claude", size: "2.4 MB" },
    { id: 2, name: "Security_Audit_2024", model: "gemini", size: "1.8 MB" },
    { id: 3, name: "Client_Meeting_Analysis", model: "gpt", size: "892 KB" }
  ];

  // Auto-initialize session on startup
  useEffect(() => {
    const initSession = async () => {
      try {
        await invoke("initialize_session");
        setSessionInitialized(true);
        console.log("✅ Session initialized - vault unlocked");
      } catch (err) {
        console.error("❌ Session initialization failed:", err);
        // Retry after 2 seconds
        setTimeout(initSession, 2000);
      }
    };
    initSession();
  }, []);

  useEffect(() => {
    invoke("get_system_status")
      .then(setStatus)
      .catch(err => console.error("Failed to get status:", err));
    
    // Load conversation history after session initialized
    if (sessionInitialized) {
      invoke("query_history", { limit: 50 })
        .then(history => {
          setConversationHistory(history);
          console.log("📜 Loaded", history.length, "conversations from database");
        })
        .catch(err => console.error("Failed to load history:", err));
    }
  }, [sessionInitialized]); // Re-fetch status after session init

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isProcessing) return;

    // Wait for session to be initialized
    if (!sessionInitialized) {
      console.warn("⏳ Waiting for session initialization...");
      return;
    }

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
        timestamp: new Date(),
        model: selectedModel
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

  const handleLoadConversation = async (item) => {
    try {
      console.log("🔄 Loading conversation:", item.id);
      console.log("📦 Encrypted content:", item.content.substring(0, 50));
      
      // Decrypt the encrypted content
      const decryptedContent = await invoke("decrypt_memory", { encryptedVal: item.content });
      
      console.log("🔓 Decrypted content:", decryptedContent);
      
      // Load as a single message for now (in reality, you'd parse conversation history)
      const loadedMessage = {
        id: item.id,
        role: "user",
        content: decryptedContent,
        timestamp: new Date(item.timestamp * 1000)
      };
      
      setMessages([loadedMessage]);
      
      console.log("✅ Loaded and decrypted conversation:", item.id, loadedMessage);
      
      // Scroll to view
      setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    } catch (err) {
      console.error("❌ Failed to decrypt conversation:", err);
      // Show error in UI
      setMessages([{
        id: Date.now(),
        role: "assistant",
        content: `Error loading conversation: ${err}`,
        timestamp: new Date()
      }]);
    }
  };

  const currentModel = models.find(m => m.id === selectedModel);

  return (
    <div className="flex h-screen bg-identra-bg text-identra-text-primary font-sans antialiased">
      
      {/* Left Sidebar - Compressed visual weight */}
      <aside className={`${sidebarOpen ? 'w-56' : 'w-0'} transition-all duration-150 bg-identra-surface border-r border-identra-border-subtle overflow-hidden flex flex-col`}>
        
        {/* Recent Section */}
        <div className="flex-1 overflow-y-auto px-3 py-6">
          <div className="flex items-center justify-between px-2 mb-4">
            <h3 className="text-[10px] font-semibold text-identra-text-secondary uppercase tracking-[0.1em]">
              Recent
            </h3>
            <Search className="w-3.5 h-3.5 text-identra-text-tertiary" />
          </div>
          <div className="space-y-0.5">
            {conversationHistory.length === 0 ? (
              <div className="px-2.5 py-4 text-center">
                <p className="text-[10px] text-identra-text-muted">No conversations yet</p>
              </div>
            ) : (
              conversationHistory.map((item) => {
                const timestamp = new Date(item.timestamp * 1000);
                const timeAgo = Math.floor((Date.now() - timestamp) / 1000 / 60);
                const timeStr = timeAgo < 60 ? `${timeAgo}m ago` : 
                               timeAgo < 1440 ? `${Math.floor(timeAgo / 60)}h ago` : 
                               `${Math.floor(timeAgo / 1440)}d ago`;
                
                // Show first 30 chars of content as title
                const title = item.content.substring(0, 30) + (item.content.length > 30 ? '...' : '');
                
                return (
                  <div 
                    key={item.id} 
                    onClick={() => handleLoadConversation(item)}
                    className="px-2.5 py-2.5 hover:bg-identra-surface-hover cursor-pointer transition-all duration-75 group border-l-2 border-transparent hover:border-identra-primary"
                  >
                    <div className="flex items-center gap-2.5 mb-1">
                      <FileText className="w-3.5 h-3.5 text-identra-text-tertiary group-hover:text-identra-text-secondary" />
                      <p className="text-xs text-identra-text-secondary group-hover:text-identra-text-primary font-medium line-clamp-1">
                        {title}
                      </p>
                    </div>
                    <p className="text-[10px] text-identra-text-muted pl-6">{timeStr}</p>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Reasoning Engine - Infrastructure configuration */}
        <div className="px-3 py-5 border-t border-identra-border-subtle">
          <div className="text-[10px] font-semibold text-identra-text-secondary uppercase tracking-[0.1em] px-2 mb-3.5">
            Reasoning Engine
          </div>
          <div className="space-y-1">
            {models.map((model) => (
              <button
                key={model.id}
                onClick={() => setSelectedModel(model.id)}
                className={`w-full flex items-center gap-2.5 px-2.5 py-2 text-xs transition-all duration-75 border-l-2 ${
                  selectedModel === model.id
                    ? 'bg-identra-surface-elevated text-identra-text-primary border-identra-primary font-medium'
                    : 'text-identra-text-tertiary hover:bg-identra-surface-hover hover:text-identra-text-secondary border-transparent font-normal'
                }`}
              >
                <div className={`w-1.5 h-1.5 rounded-full ${selectedModel === model.id ? 'bg-identra-active' : 'bg-identra-border'}`}></div>
                <span className="flex-1 text-left">{model.name}</span>
              </button>
            ))}
          </div>
        </div>

      </aside>

      {/* Main Content Area - Expanded workspace */}
      <main className="flex-1 flex flex-col min-w-0">
        
        {/* Minimal Top Bar */}
        <header className="h-12 border-b border-identra-border-subtle flex items-center justify-between px-8 bg-identra-bg">
          <div className="text-[10px] text-identra-text-tertiary tracking-[0.12em] font-semibold">
            IDENTRA OS
          </div>
          <button className="p-1.5 hover:bg-identra-surface-hover transition-colors duration-75 rounded">
            <MoreVertical className="w-4 h-4 text-identra-text-tertiary" />
          </button>
        </header>

        {/* Messages Area - Central workspace dominance */}
        <div className="flex-1 overflow-y-auto px-12 py-12">
          <div className="max-w-5xl mx-auto">
            {messages.length === 0 ? (
              // Empty State - System readiness
              <div className="flex flex-col justify-center h-full pt-32">
                <h3 className="text-2xl font-semibold text-identra-text-primary mb-2 tracking-tight">
                  Deep Work Console
                </h3>
                <p className="text-sm text-identra-text-tertiary leading-relaxed max-w-md">
                  Expands into a distraction-free environment where context is king.
                </p>
              </div>
            ) : (
              // Messages
              <div className="space-y-8">
                {messages.map((msg) => (
                  <div 
                    key={msg.id} 
                    className={`flex flex-col gap-1 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
                  >
                    <div className="max-w-3xl w-full">
                      <div className={`px-0 py-0 ${
                        msg.role === 'user' 
                          ? 'text-identra-text-primary' 
                          : 'text-identra-text-primary'
                      }`}>
                        <p className="text-base leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                      </div>
                      <div className="flex items-center gap-2 mt-2">
                        {msg.model && (
                          <span className="text-[9px] text-identra-text-muted uppercase tracking-wider">
                            {models.find(m => m.id === msg.model)?.name}
                          </span>
                        )}
                        <span className="text-[9px] text-identra-text-muted">
                          {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
                
                {isProcessing && (
                  <div className="flex flex-col gap-1">
                    <div className="max-w-3xl">
                      <div className="py-2">
                        <div className="flex gap-1">
                          <span className="w-1 h-1 bg-identra-text-muted rounded-full"></span>
                          <span className="w-1 h-1 bg-identra-text-muted rounded-full"></span>
                          <span className="w-1 h-1 bg-identra-text-muted rounded-full"></span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
        </div>

        {/* Input Area - Command interface */}
        <div className="border-t border-identra-border-subtle px-12 py-5 bg-identra-bg">
          <div className="max-w-5xl mx-auto">
            <div className="relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type a message to Identra..."
                className="w-full bg-identra-surface border border-identra-border focus:border-identra-primary rounded px-4 py-3 text-sm text-identra-text-primary placeholder:text-identra-text-tertiary outline-none transition-all duration-75 focus:bg-identra-surface-elevated"
                disabled={isProcessing}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isProcessing}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-identra-text-tertiary hover:text-identra-text-primary disabled:text-identra-text-disabled hover:bg-identra-surface-hover rounded transition-all duration-75"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Footer Status Bar */}
        <div className="h-7 border-t border-identra-border-subtle flex items-center justify-center bg-identra-surface">
          <div className="flex items-center gap-2.5 text-[10px] text-identra-text-tertiary tracking-[0.1em] font-semibold">
            <span>IDENTRA OS V1.0</span>
            <span className="text-identra-text-muted">•</span>
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-identra-active"></div>
              <span>SECURE ENCLAVE ACTIVE</span>
            </div>
          </div>
        </div>

      </main>

      {/* Right Context Panel - Control plane */}
      <aside className={`${contextPanelOpen ? 'w-64' : 'w-0'} transition-all duration-150 bg-identra-surface border-l border-identra-border-subtle overflow-hidden flex flex-col`}>
        
        <div className="h-12 flex items-center justify-between px-4 border-b border-identra-border-subtle">
          <h3 className="text-[10px] font-semibold text-identra-text-secondary uppercase tracking-[0.1em]">
            Model Context
          </h3>
          <button 
            onClick={() => setContextPanelOpen(false)}
            className="text-identra-text-tertiary hover:text-identra-text-secondary p-1 hover:bg-identra-surface-hover rounded transition-all duration-75"
          >
            <ChevronDown className="w-3.5 h-3.5 rotate-90" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
          {contextDocuments.map((doc) => {
            const docModel = models.find(m => m.id === doc.model);
            return (
              <div 
                key={doc.id}
                className="px-3 py-2.5 bg-identra-surface-elevated border border-identra-border hover:border-identra-primary transition-all duration-75 cursor-pointer group"
              >
                <div className="flex items-start gap-2.5 mb-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-identra-active shrink-0 mt-1.5"></div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-identra-text-primary font-medium truncate group-hover:text-identra-text-primary">
                      {doc.name}
                    </p>
                    <p className="text-[10px] text-identra-text-muted mt-1">
                      {doc.size}
                    </p>
                  </div>
                </div>
                <div className="flex items-center justify-between border-t border-identra-border-subtle pt-2 mt-2">
                  <span className="text-[10px] text-identra-text-tertiary uppercase tracking-wider font-medium">
                    {docModel.name}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        <div className="px-4 py-3.5 border-t border-identra-border-subtle">
          <div className="flex items-center justify-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-identra-active"></div>
            <div className="text-[10px] text-identra-text-tertiary text-center tracking-[0.1em] font-semibold">
              CROSS-MODEL SYNC ACTIVE
            </div>
          </div>
        </div>

      </aside>
    </div>
  );
}

