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
  const [contextPanelOpen, setContextPanelOpen] = useState(true);
  const [selectedModel, setSelectedModel] = useState("claude"); // claude, gemini, gpt
  const [modelMenuOpen, setModelMenuOpen] = useState(false);
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

  useEffect(() => {
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

  const currentModel = models.find(m => m.id === selectedModel);

  return (
    <div className="flex h-screen bg-identra-bg text-identra-text-primary font-sans antialiased">

      {/* Left sidebar: Identra, user profile, reasoning engine */}
      <aside className="w-64 bg-identra-surface border-r border-identra-border-subtle flex flex-col px-5 py-5">
        <div className="flex items-center gap-3 mb-6">
          <div className="identra-logo-slot" />
          <div className="identra-title-block">
            <div className="identra-title">IDENTRA</div>
            <div className="identra-user-label">OS Console</div>
          </div>
        </div>

        <div className="mb-6">
          <button className="identra-profile w-full justify-between">
            <div className="flex items-center gap-2.5">
              <div className="identra-avatar" />
              <div className="identra-profile-text">
                <span className="identra-profile-name">You</span>
                <span className="identra-profile-meta">Profile details</span>
              </div>
            </div>
            <ChevronDown className="w-3 h-3 text-identra-text-tertiary" />
          </button>
        </div>

        <div className="mt-auto">
          <div className="model-box-label mb-2">Reasoning engine</div>
          <div
            className="model-box w-full justify-between"
            onClick={() => setModelMenuOpen((open) => !open)}
          >
            <div className="model-box-value">
              {currentModel?.name || "Claude 3.5 Sonnet"}
            </div>
            <ChevronDown className="w-3 h-3 text-identra-text-tertiary" />

            {modelMenuOpen && (
              <div className="model-box-menu" onClick={(e) => e.stopPropagation()}>
                {models.map((model) => (
                  <button
                    key={model.id}
                    className="model-box-item"
                    onClick={() => {
                      setSelectedModel(model.id);
                      setModelMenuOpen(false);
                    }}
                  >
                    {model.name}
                    <span>
                      {model.id === "claude"
                        ? "Claude 3.5 Sonnet"
                        : model.id === "gemini"
                        ? "Gemini 1.5 Pro"
                        : "GPT‑4.0 / 4o"}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Middle: conversation */}
      <main className="flex-1 flex flex-col min-w-0">

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto px-12 py-10">
          <div className="max-w-5xl mx-auto">
            {messages.length === 0 ? (
              <div className="flex flex-col justify-center h-full pt-32">
                <h3 className="text-2xl font-semibold text-identra-text-primary mb-2 tracking-tight">
                  Talk to Identra OS
                </h3>
                <p className="text-sm text-identra-text-tertiary leading-relaxed max-w-md">
                  Ask anything about your work, and keep the conversation flowing in a calm, focused space.
                </p>
              </div>
            ) : (
              <div className="space-y-8">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex flex-col gap-1 ${
                      msg.role === "user" ? "items-end" : "items-start"
                    }`}
                  >
                    <div className="max-w-[60%]">
                      <div
                        className={`chat-bubble ${
                          msg.role === "user"
                            ? "chat-bubble-user text-identra-text-primary"
                            : "chat-bubble-assistant text-identra-text-primary"
                        }`}
                      >
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                      </div>
                      <div className="flex items-center gap-2 mt-2 text-right">
                        {msg.model && (
                          <span className="text-[9px] text-identra-text-muted uppercase tracking-wider">
                            {models.find((m) => m.id === msg.model)?.name}
                          </span>
                        )}
                        <span className="text-[9px] text-identra-text-muted">
                          {msg.timestamp.toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}

                {isProcessing && (
                  <div className="flex flex-col gap-1 items-start">
                    <div className="max-w-[60%]">
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

        {/* Input Area */}
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

      {/* Right: model context on top, recent at bottom */}
      <aside
        className={`${
          contextPanelOpen ? "w-72" : "w-0"
        } transition-all duration-150 bg-identra-surface border-l border-identra-border-subtle overflow-hidden flex flex-col`}
      >
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
            const docModel = models.find((m) => m.id === doc.model);
            return (
              <div
                key={doc.id}
                className="px-3 py-2.5 bg-identra-surface-elevated border border-identra-border hover:border-identra-active transition-all duration-75 cursor-pointer group"
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
          <div className="recent-panel">
            <div className="recent-panel-header">
              <span>Recent</span>
              <Search className="w-3.5 h-3.5 text-identra-text-tertiary" />
            </div>
            <div className="mt-1 space-y-1">
              <div className="recent-item">
                <div className="recent-item-title">Project Alpha</div>
                <div className="recent-item-meta">2h ago</div>
              </div>
              <div className="recent-item">
                <div className="recent-item-title">API Integration</div>
                <div className="recent-item-meta">1d ago</div>
              </div>
              <div className="recent-item">
                <div className="recent-item-title">Q4 Report</div>
                <div className="recent-item-meta">3d ago</div>
              </div>
            </div>
          </div>
        </div>

        <div className="px-4 py-3 border-t border-identra-border-subtle">
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
