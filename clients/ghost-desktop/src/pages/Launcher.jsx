import { useState, useEffect, useRef } from "react";
import { Command, Zap, Shield } from "lucide-react";
import { invoke } from "@tauri-apps/api/core";

export default function Launcher() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const inputRef = useRef(null);
  const messagesEndRef = useRef(null);

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
      padding: '16px',
      background: 'transparent',
      overflow: 'hidden'
    }}>
      <div className="w-full max-w-3xl flex flex-col gap-3"style={{ background: 'transparent' }}>
        
        {/* Messages Area - Only show when there are messages */}
        {messages.length > 0 && (
          <div className="bg-identra-bg/95 backdrop-blur-3xl border border-identra-border/60 rounded-2xl shadow-[0_20px_80px_rgba(0,0,0,0.9)] p-4 max-h-[400px] overflow-y-auto space-y-3">
            {messages.map((msg) => (
              <div 
                key={msg.id} 
                className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}
              >
                {msg.role === 'assistant' && (
                  <div className="w-6 h-6 rounded-full bg-identra-accent/20 flex items-center justify-center shrink-0 mt-1">
                    <Shield className="w-3 h-3 text-identra-accent" />
                  </div>
                )}
                <div className={`px-4 py-2 rounded-2xl max-w-[80%] ${
                  msg.role === 'user' 
                    ? 'bg-identra-accent text-white' 
                    : 'bg-identra-surface border border-identra-border'
                }`}>
                  <p className="text-sm leading-relaxed">{msg.content}</p>
                </div>
              </div>
            ))}
            {isProcessing && (
              <div className="flex gap-3">
                <div className="w-6 h-6 rounded-full bg-identra-accent/20 flex items-center justify-center shrink-0">
                  <Shield className="w-3 h-3 text-identra-accent animate-pulse" />
                </div>
                <div className="px-4 py-2 rounded-2xl bg-identra-surface border border-identra-border">
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
        )}

        {/* Input Bar - Always visible */}
        <form onSubmit={handleSubmit}>
          <div className="relative flex items-center bg-identra-bg/95 backdrop-blur-3xl border border-identra-border/60 rounded-full shadow-[0_20px_80px_rgba(0,0,0,0.9)] px-6 py-4 transition-all duration-200 hover:border-identra-accent/30">
            <Command 
              className={`w-5 h-5 transition-colors mr-4 ${
                isProcessing ? 'text-identra-accent animate-pulse' : 'text-identra-text-muted'
              }`} 
            />
            
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask Identra anything..."
              className="flex-1 bg-transparent text-base text-identra-text-primary placeholder-identra-text-muted/40 border-none outline-none font-light"
              autoComplete="off"
              disabled={isProcessing}
            />

            {query && (
              <div className="ml-3 flex items-center gap-2">
                <kbd className="px-2 py-1 bg-identra-surface/60 border border-identra-border/50 rounded text-[10px] text-identra-text-muted font-mono">
                  ↵
                </kbd>
              </div>
            )}
            
            {isProcessing && (
              <Zap className="w-4 h-4 text-identra-accent animate-pulse ml-3" />
            )}
          </div>
        </form>
        
        {/* Hint text - Only show when no messages */}
        {messages.length === 0 && (
          <div className="flex flex-col items-center gap-2">
            <div className="text-center text-[10px] text-identra-text-muted/60 font-mono">
              ESC to close • Alt+Space to reopen
            </div>
            <button
              onClick={() => {
                invoke("toggle_main_window");
                invoke("toggle_launcher");
              }}
              className="text-[10px] text-identra-accent/70 hover:text-identra-accent font-mono underline"
            >
              Open Full Chat Interface
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
