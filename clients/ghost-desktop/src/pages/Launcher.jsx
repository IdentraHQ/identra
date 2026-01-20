import { useState, useEffect, useRef } from "react";
import { Command, ArrowRight } from "lucide-react";
import { invoke } from "@tauri-apps/api/core";

export default function Launcher() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const inputRef = useRef(null);
  const messagesEndRef = useRef(null);

  const quickActions = [
    { id: 1, text: "Summarize last meeting notes", label: "SUMMARIZE" },
    { id: 2, text: 'Search for "Authentication"', label: "SEARCH" }
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
      padding: '40px',
      background: 'transparent',
      overflow: 'hidden'
    }}>
      <div className="w-full max-w-3xl flex flex-col gap-5 items-center" style={{ background: 'transparent' }}>
        
        {/* Title - Refined typography */}
        <div className="text-center space-y-1.5">
          <h1 className="text-2xl font-semibold text-identra-text-primary tracking-tight">
            Instant Invocation
          </h1>
          <p className="text-xs text-identra-text-tertiary tracking-wide">
            <kbd className="px-1.5 py-0.5 bg-identra-surface-elevated border border-identra-border text-[10px] font-mono">Alt</kbd>
            {' + '}
            <kbd className="px-1.5 py-0.5 bg-identra-surface-elevated border border-identra-border text-[10px] font-mono">Space</kbd>
            {' • Always robust, never intrusive'}
          </p>
        </div>

        {/* Search Box - More refined */}
        <div className="w-full bg-identra-bg border border-identra-border shadow-2xl overflow-hidden">
          <form onSubmit={handleSubmit}>
            <div className="flex items-center gap-3 px-5 py-3.5">
              <Command className="w-4 h-4 text-identra-text-tertiary shrink-0" strokeWidth={2} />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask Identra..."
                className="flex-1 bg-transparent text-identra-text-primary placeholder:text-identra-text-tertiary outline-none text-sm"
                disabled={isProcessing}
                autoFocus
              />
              {isProcessing && (
                <div className="flex gap-1">
                  <span className="w-1 h-1 bg-identra-text-muted rounded-full"></span>
                  <span className="w-1 h-1 bg-identra-text-muted rounded-full"></span>
                  <span className="w-1 h-1 bg-identra-text-muted rounded-full"></span>
                </div>
              )}
            </div>
          </form>
        </div>

        {/* Quick Actions - Infrastructure style */}
        {messages.length === 0 && (
          <div className="w-full space-y-1.5">
            {quickActions.map((action) => (
              <button
                key={action.id}
                onClick={() => setQuery(action.text)}
                className="w-full px-4 py-2.5 bg-identra-surface border border-identra-border hover:border-identra-primary hover:bg-identra-surface-hover transition-all duration-75 text-left flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <span className="text-[9px] text-identra-text-tertiary font-semibold tracking-wider uppercase">
                    {action.label}
                  </span>
                  <span className="text-xs text-identra-text-secondary group-hover:text-identra-text-primary">
                    {action.text}
                  </span>
                </div>
                <ArrowRight className="w-3 h-3 text-identra-text-muted group-hover:text-identra-text-secondary transition-colors" />
              </button>
            ))}
          </div>
        )}

        {/* Messages - Professional layout */}
        {messages.length > 0 && (
          <div className="w-full bg-identra-bg border border-identra-border shadow-2xl p-5 max-h-[450px] overflow-y-auto space-y-3">
            {messages.map((msg) => (
              <div 
                key={msg.id} 
                className={`flex flex-col gap-1 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
              >
                <div className={`px-3 py-2 max-w-[90%] ${
                  msg.role === 'user' 
                    ? 'bg-identra-surface-elevated border border-identra-border text-identra-text-primary' 
                    : 'text-identra-text-primary'
                }`}>
                  <p className="text-sm leading-relaxed">{msg.content}</p>
                </div>
              </div>
            ))}
            {isProcessing && (
              <div className="flex flex-col gap-1">
                <div className="px-3 py-2">
                  <div className="flex gap-1">
                    <span className="w-1 h-1 bg-identra-text-muted rounded-full"></span>
                    <span className="w-1 h-1 bg-identra-text-muted rounded-full"></span>
                    <span className="w-1 h-1 bg-identra-text-muted rounded-full"></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}

        {/* Footer Status - Compact */}
        <div className="flex items-center gap-2 text-[9px] text-identra-text-muted tracking-[0.1em] font-semibold">
          <span>IDENTRA OS V1.0</span>
          <span>•</span>
          <div className="flex items-center gap-1.5">
            <div className="w-1 h-1 rounded-full bg-identra-active"></div>
            <span>SECURE ENCLAVE ACTIVE</span>
          </div>
        </div>

      </div>
    </div>
  );
}
