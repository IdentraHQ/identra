import { useState, useEffect, useRef } from "react";
import { Search, Zap } from "lucide-react";
import { invoke } from "@tauri-apps/api/core";

export default function Launcher() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const inputRef = useRef(null);
  const messagesEndRef = useRef(null);

  const quickActions = [
    { id: 1, text: "Summarize last meeting notes", icon: "📝" },
    { id: 2, text: 'Search for "Authentication"', icon: "🔍" }
  ];

  useEffect(() => {
    // Auto-focus on mount
    inputRef.current?.focus();

    // Listen for Escape to close
    const handleEsc = (e) => {
      if (e.key === 'Escape') {
        invoke("toggle_launcher").catch(console.error);
        setQuery("");
        setMessages([]);
      }
    };
    globalThis.addEventListener('keydown', handleEsc);
    return () => globalThis.removeEventListener('keydown', handleEsc);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim() || isProcessing) return;

    const userMessage = {
      id: Date.now(),
      role: "user",
      content: query
    };

    setMessages(prev => [...prev, userMessage]);
    setQuery("");
    setIsProcessing(true);

    try {
      const response = await invoke("vault_memory", { content: userMessage.content });
      
      const assistantMessage = {
        id: Date.now() + 1,
        role: "assistant",
        content: response
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      console.error("Error:", err);
      const errorMessage = {
        id: Date.now() + 1,
        role: "assistant",
        content: `Error: ${err}`
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div style={{ 
      minHeight: '100vh', 
      width: '100vw', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center', 
      padding: '32px',
      background: 'transparent',
      overflow: 'hidden'
    }}>
      <div className="w-full max-w-2xl flex flex-col gap-6 items-center" style={{ background: 'transparent' }}>
        
        {/* Title */}
        <div className="text-center space-y-2 animate-fade-in">
          <h1 className="text-3xl font-light text-identra-text-primary tracking-tight">
            Instant Invocation
          </h1>
          <p className="text-sm text-identra-text-tertiary">
            Summon Identra via <kbd className="px-2 py-0.5 bg-identra-surface-elevated border border-identra-border rounded text-xs font-mono">Win</kbd> + <kbd className="px-2 py-0.5 bg-identra-surface-elevated border border-identra-border rounded text-xs font-mono">K</kbd> Always robust, never intrusive.
          </p>
        </div>

        {/* Search Box */}
        <div className="w-full bg-identra-bg/98 backdrop-blur-2xl border border-identra-border-subtle rounded-2xl shadow-[0_32px_128px_rgba(0,0,0,0.8)] overflow-hidden animate-slide-up">
          <form onSubmit={handleSubmit}>
            <div className="flex items-center gap-4 px-6 py-4">
              <Zap className="w-5 h-5 text-identra-text-tertiary shrink-0" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask Identra..."
                className="flex-1 bg-transparent text-identra-text-primary placeholder:text-identra-text-muted outline-none text-base"
                disabled={isProcessing}
                autoFocus
              />
              {isProcessing && (
                <div className="flex gap-1">
                  <span className="w-1.5 h-1.5 bg-identra-text-muted rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                  <span className="w-1.5 h-1.5 bg-identra-text-muted rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                  <span className="w-1.5 h-1.5 bg-identra-text-muted rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                </div>
              )}
            </div>
          </form>
        </div>

        {/* Quick Actions - Only show when no messages */}
        {messages.length === 0 && (
          <div className="w-full space-y-2 animate-fade-in">
            {quickActions.map((action) => (
              <button
                key={action.id}
                onClick={() => setQuery(action.text)}
                className="w-full px-5 py-3 bg-identra-surface-elevated/80 backdrop-blur-xl hover:bg-identra-surface-hover border border-identra-border-subtle rounded-xl text-left transition-all group flex items-center gap-3"
              >
                <span className="text-lg">{action.icon}</span>
                <span className="text-sm text-identra-text-secondary group-hover:text-identra-text-primary">
                  {action.text}
                </span>
              </button>
            ))}
          </div>
        )}

        {/* Messages - Show above search when present */}
        {messages.length > 0 && (
          <div className="w-full bg-identra-bg/98 backdrop-blur-2xl border border-identra-border-subtle rounded-2xl shadow-[0_32px_128px_rgba(0,0,0,0.8)] p-6 max-h-[400px] overflow-y-auto space-y-4 animate-slide-down">
            {messages.map((msg) => (
              <div 
                key={msg.id} 
                className={`flex flex-col gap-1 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
              >
                <div className={`px-4 py-2.5 rounded-xl max-w-[85%] ${
                  msg.role === 'user' 
                    ? 'bg-identra-surface-elevated text-identra-text-primary' 
                    : 'text-identra-text-primary'
                }`}>
                  <p className="text-sm leading-relaxed">{msg.content}</p>
                </div>
              </div>
            ))}
            {isProcessing && (
              <div className="flex flex-col gap-1">
                <div className="px-4 py-2.5 rounded-xl">
                  <div className="flex gap-1.5">
                    <span className="w-1.5 h-1.5 bg-identra-text-muted rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                    <span className="w-1.5 h-1.5 bg-identra-text-muted rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                    <span className="w-1.5 h-1.5 bg-identra-text-muted rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}

        {/* Footer Status */}
        <div className="flex items-center gap-2 text-[10px] text-identra-text-muted tracking-wider animate-fade-in">
          <span>IDENTRA OS V1.0</span>
          <span>•</span>
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-identra-active animate-pulse-subtle"></div>
            <span>SECURE ENCLAVE ACTIVE</span>
          </div>
        </div>

      </div>
    </div>
  );
}
