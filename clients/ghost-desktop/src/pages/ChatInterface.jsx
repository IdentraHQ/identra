import { useState, useEffect, useRef } from "react";
import { 
  Send, 
  Search,
  FileText,
  ChevronDown,
  ChevronUp,
  User
} from "lucide-react";
import { invoke } from "@tauri-apps/api/core";

export default function ChatInterface() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedModel, setSelectedModel] = useState("claude"); // claude, gemini, gpt
  const [sessionInitialized, setSessionInitialized] = useState(false);
  const [conversationHistory, setConversationHistory] = useState([]);
  const [reasoningEngineOpen, setReasoningEngineOpen] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

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
    // Load conversation history after session initialized
    if (sessionInitialized) {
      invoke("query_history", { limit: 50 })
        .then(history => {
          setConversationHistory(history);
          console.log("📜 Loaded", history.length, "conversations from database");
        })
        .catch(err => console.error("Failed to load history:", err));
    }
  }, [sessionInitialized]); // Re-fetch after session init

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
      // Prepare conversation history for API
      // Note: Context limit is configured in .env (CHAT_CONTEXT_LIMIT, default: 10)
      const historyForAPI = messages.slice(-10).map(msg => ({
        role: msg.role,
        content: msg.content,
        timestamp: Math.floor(msg.timestamp.getTime() / 1000)
      }));

      // Call the new chat_with_ai command
      const response = await invoke("chat_with_ai", {
        message: input,
        model: selectedModel,
        conversationHistory: historyForAPI
      });
      
      const assistantMessage = {
        id: Date.now() + 1,
        role: "assistant",
        content: response.message,
        timestamp: new Date(),
        model: selectedModel
      };

      setMessages(prev => [...prev, assistantMessage]);
      
      // Refresh history to show the new conversation
      invoke("query_history", { limit: 50 })
        .then(history => {
          setConversationHistory(history);
        })
        .catch(err => console.error("Failed to refresh history:", err));
        
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

  // Auto-resize textarea based on content
  useEffect(() => {
    if (textareaRef.current) {
      // Reset height to auto to get the correct scrollHeight
      textareaRef.current.style.height = 'auto';
      // Set height to scrollHeight, but respect min and max
      const scrollHeight = textareaRef.current.scrollHeight;
      const minHeight = 80; // min-h-[80px]
      const maxHeight = 400; // max-h-[400px]
      const newHeight = Math.min(Math.max(scrollHeight, minHeight), maxHeight);
      textareaRef.current.style.height = `${newHeight}px`;
    }
  }, [input]);

  const handleLoadConversation = async (item) => {
    try {
      console.log("🔄 Loading conversation:", item.id);
      console.log("📦 Encrypted content:", item.content.substring(0, 50));
      
      // Decrypt the encrypted content
      const decryptedContent = await invoke("decrypt_memory", { encryptedVal: item.content });
      
      console.log("🔓 Decrypted content:", decryptedContent);
      
      // Parse the conversation JSON
      try {
        const conversation = JSON.parse(decryptedContent);
        
        // Load both user message and AI response
        const loadedMessages = [];
        
        if (conversation.user) {
          loadedMessages.push({
            id: `${item.id}-user`,
            role: "user",
            content: conversation.user,
            timestamp: new Date(conversation.timestamp || item.timestamp * 1000)
          });
        }
        
        if (conversation.assistant) {
          loadedMessages.push({
            id: `${item.id}-assistant`,
            role: "assistant",
            content: conversation.assistant,
            timestamp: new Date(conversation.timestamp || item.timestamp * 1000),
            model: conversation.model || selectedModel
          });
        }
        
        setMessages(loadedMessages);
        
        console.log("✅ Loaded conversation with", loadedMessages.length, "messages");
      } catch (error_) {
        console.warn("Not JSON format, treating as legacy:", error_.message);
        // If it's not JSON, treat it as a single user message (legacy format)
        const loadedMessage = {
          id: item.id,
          role: "user",
          content: decryptedContent,
          timestamp: new Date(item.timestamp * 1000)
        };
        
        setMessages([loadedMessage]);
        console.log("✅ Loaded legacy conversation:", item.id);
      }
      
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
      
      {/* Left Section - Branding and User Profile */}
      <aside className="w-64 bg-identra-surface border-r border-identra-border-subtle flex flex-col">
        {/* IDENTRA Branding */}
        <div className="px-6 py-8 border-b border-identra-border-subtle">
          <h1 className="text-4xl font-bold text-identra-text-primary tracking-tight mb-2">
            IDENTRA
          </h1>
        </div>

        {/* User Profile and Pack Name */}
        <div className="px-6 py-6 border-b border-identra-border-subtle">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-full bg-identra-surface-elevated border border-identra-border flex items-center justify-center">
              <User className="w-6 h-6 text-identra-text-secondary" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-identra-text-primary">User Profile</p>
              <p className="text-xs text-identra-text-tertiary mt-0.5">Active Session</p>
            </div>
          </div>
          <div className="px-3 py-2 bg-identra-surface-elevated border border-identra-border rounded">
            <p className="text-[10px] text-identra-text-tertiary uppercase tracking-wider mb-1">Pack</p>
            <p className="text-sm text-identra-text-primary font-medium">Standard Pack</p>
          </div>
        </div>

        {/* Spacer */}
        <div className="flex-1"></div>
      </aside>

      {/* Middle Section - Chat Conversation */}
      <main className="flex-1 flex flex-col min-w-0 border-r border-identra-border-subtle">
        {/* Reasoning Engine - At top of chat section */}
        <div className="px-8 py-4 border-b border-identra-border-subtle bg-identra-surface">
          <button
            onClick={() => setReasoningEngineOpen(!reasoningEngineOpen)}
            className="w-full max-w-md flex items-center justify-between px-4 py-2.5 bg-identra-surface-elevated border border-identra-border hover:border-identra-primary transition-all duration-75 rounded"
          >
            <div className="flex items-center gap-3">
              <span className="text-[10px] font-semibold text-identra-text-secondary uppercase tracking-[0.1em]">
                Reasoning Engine
              </span>
              <span className="text-sm text-identra-text-primary font-medium">
                {currentModel.name}
              </span>
            </div>
            {reasoningEngineOpen ? (
              <ChevronUp className="w-4 h-4 text-identra-text-tertiary" />
            ) : (
              <ChevronDown className="w-4 h-4 text-identra-text-tertiary" />
            )}
          </button>
          
          {reasoningEngineOpen && (
            <div className="mt-3 max-w-md space-y-1 bg-identra-surface-elevated border border-identra-border rounded p-2">
              {models.map((model) => (
                <button
                  key={model.id}
                  onClick={() => {
                    setSelectedModel(model.id);
                    setReasoningEngineOpen(false);
                  }}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 text-sm transition-all duration-75 rounded ${
                    selectedModel === model.id
                      ? 'bg-identra-surface text-identra-text-primary border border-identra-primary font-medium'
                      : 'text-identra-text-tertiary hover:bg-identra-surface-hover hover:text-identra-text-secondary font-normal'
                  }`}
                >
                  <div className={`w-1.5 h-1.5 rounded-full ${selectedModel === model.id ? 'bg-identra-active' : 'bg-identra-border'}`}></div>
                  <span className="flex-1 text-left">{model.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Messages Area - Split Layout */}
        <div className="flex-1 overflow-y-auto px-8 py-8">
          {messages.length === 0 ? (
            <div className="flex flex-col justify-center h-full items-center">
              <h3 className="text-2xl font-semibold text-identra-text-primary mb-2 tracking-tight">
                Deep Work Console
              </h3>
              <p className="text-sm text-identra-text-tertiary leading-relaxed max-w-md text-center">
                Expands into a distraction-free environment where context is king.
              </p>
            </div>
          ) : (
            <div className="space-y-6 max-w-full">
              {messages.map((msg) => (
                <div 
                  key={msg.id} 
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className="w-[60%] flex flex-col gap-2">
                    <div className={`px-4 py-3 rounded-lg ${
                      msg.role === 'user' 
                        ? 'bg-identra-surface-elevated border border-identra-border text-identra-text-primary ml-auto' 
                        : 'bg-identra-surface border border-identra-border-subtle text-identra-text-primary mr-auto'
                    }`}>
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                    </div>
                    <div className={`flex items-center gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
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
                <div className="flex justify-start">
                  <div className="w-[60%] flex flex-col gap-2">
                    <div className="px-4 py-3 bg-identra-surface border border-identra-border-subtle rounded-lg mr-auto">
                      <div className="flex gap-1">
                        <span className="w-1.5 h-1.5 bg-identra-text-muted rounded-full animate-pulse"></span>
                        <span className="w-1.5 h-1.5 bg-identra-text-muted rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></span>
                        <span className="w-1.5 h-1.5 bg-identra-text-muted rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-identra-border-subtle px-8 py-6 bg-identra-bg">
          <div className="relative max-w-5xl mx-auto">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Type a message to Identra..."
              className="w-full bg-identra-surface border border-identra-border focus:border-identra-primary rounded-lg px-4 py-4 pr-12 text-sm text-identra-text-primary placeholder:text-identra-text-tertiary outline-none transition-all duration-75 focus:bg-identra-surface-elevated resize overflow-y-auto"
              disabled={isProcessing}
              style={{ minHeight: '80px', maxHeight: '400px', resize: 'both' }}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isProcessing}
              className="absolute right-3 bottom-3 p-2.5 text-identra-text-tertiary hover:text-identra-text-primary disabled:text-identra-text-disabled hover:bg-identra-surface-hover rounded transition-all duration-75"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </main>

      {/* Right Section - Model Context and Recent Chats */}
      <aside className="w-72 bg-identra-surface border-l border-identra-border-subtle flex flex-col">
        {/* Model Context and Audits */}
        <div className="px-4 py-5 border-b border-identra-border-subtle">
          <h3 className="text-[10px] font-semibold text-identra-text-secondary uppercase tracking-[0.1em] mb-4">
            Model Context
          </h3>
          <div className="space-y-2.5">
            {contextDocuments.map((doc) => {
              const docModel = models.find(m => m.id === doc.model);
              return (
                <div 
                  key={doc.id}
                  className="px-3 py-2.5 bg-identra-surface-elevated border border-identra-border hover:border-identra-primary transition-all duration-75 cursor-pointer group rounded"
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

        </div>

        {/* Recent Chats */}
        <div className="flex-1 overflow-y-auto px-4 py-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-[10px] font-semibold text-identra-text-secondary uppercase tracking-[0.1em]">
              Recent Chats
            </h3>
            <Search className="w-3.5 h-3.5 text-identra-text-tertiary" />
          </div>
          <div className="space-y-2">
            {conversationHistory.length === 0 ? (
              <div className="px-3 py-6 text-center bg-identra-surface-elevated border border-identra-border rounded">
                <p className="text-[10px] text-identra-text-muted">No conversations yet</p>
              </div>
            ) : (
              conversationHistory.map((item) => {
                const timestamp = new Date(item.timestamp * 1000);
                const timeAgo = Math.floor((Date.now() - timestamp) / 1000 / 60);
                let timeStr;
                if (timeAgo < 60) {
                  timeStr = `${timeAgo}m ago`;
                } else if (timeAgo < 1440) {
                  timeStr = `${Math.floor(timeAgo / 60)}h ago`;
                } else {
                  timeStr = `${Math.floor(timeAgo / 1440)}d ago`;
                }
                
                // Try to parse and show user message as preview
                let title = "Conversation";
                
                return (
                  <button
                    key={item.id} 
                    onClick={() => handleLoadConversation(item)}
                    className="w-full px-3 py-3 bg-identra-surface-elevated border border-identra-border hover:border-identra-primary cursor-pointer transition-all duration-75 group rounded text-left"
                  >
                    <div className="flex items-center gap-2.5 mb-2">
                      <FileText className="w-3.5 h-3.5 text-identra-text-tertiary group-hover:text-identra-text-secondary" />
                      <p className="text-xs text-identra-text-secondary group-hover:text-identra-text-primary font-medium line-clamp-2 flex-1">
                        {title}
                      </p>
                    </div>
                    <p className="text-[10px] text-identra-text-muted pl-6">{timeStr}</p>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Footer Status */}
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

