import { useState, useEffect, useRef } from "react";
import { 
  Send, 
  Search,
  FileText,
  User,
  Settings,
  X,
  Moon,
  Sun,
  Circle,
  Bell,
  Shield,
  LogOut,
  ChevronDown,
  Check,
  Brain,       // New icon for Brain
  Database     // New icon for Memory
} from "lucide-react";
import { invoke } from "@tauri-apps/api/core";

// --- ICONS ---
function ClaudeIcon({ className }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <rect x="3" y="3" width="18" height="18" rx="4" ry="4" />
      <circle cx="12" cy="12" r="4" />
    </svg>
  );
}
function GeminiIcon({ className }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 2L14.5 8.5L21 9L16 13.5L17.5 20L12 16.5L6.5 20L8 13.5L3 9L9.5 8.5L12 2Z" />
    </svg>
  );
}
function OpenAIIcon({ className }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M12 2L4 8V16L12 22L20 16V8L12 2Z" />
    </svg>
  );
}
const modelIcons = { claude: ClaudeIcon, gemini: GeminiIcon, gpt: OpenAIIcon };

export default function ChatInterface() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedModel, setSelectedModel] = useState("claude"); 
  const [profileOpen, setProfileOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [themeOpen, setThemeOpen] = useState(false);
  const [rightPanelOpen, setRightPanelOpen] = useState(true);
  const [theme, setTheme] = useState("dark");
  
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Apply theme
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  // Models
  const models = [
    { id: "claude", name: "Identra Brain (Local)", color: "identra-claude" }, // Renamed for clarity
    { id: "gemini", name: "Gemini 1.5 Pro", color: "identra-gemini" },
    { id: "gpt", name: "GPT-4o", color: "identra-gpt" }
  ];

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // --- NEW: HANDLE SEND VIA LOCAL BRAIN API ---
  const handleSend = async () => {
    if (!input.trim() || isProcessing) return;

    // 1. Add User Message to UI
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
      // 2. Call the Python Brain Service (Localhost:8001)
      // We bypass the Rust backend for now to talk directly to your new RAG engine
      const response = await fetch("http://localhost:8001/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_message: userMessage.content,
          user_id: "sailesh_admin" // Hardcoded for now, can be dynamic later
        })
      });

      if (!response.ok) {
        throw new Error(`Brain Service Offline: ${response.statusText}`);
      }

      const data = await response.json();

      // 3. Add AI Response to UI
      const assistantMessage = {
        id: Date.now() + 1,
        role: "assistant",
        content: data.ai_response,
        timestamp: new Date(),
        model: "claude", // Using Claude icon for Identra Brain
        // Extra RAG Metadata (To show memories were used)
        memoryDepth: data.memory_depth || 0,
        contextSummary: data.context_summary || ""
      };

      setMessages(prev => [...prev, assistantMessage]);

    } catch (err) {
      console.error("Brain Error:", err);
      const errorMessage = {
        id: Date.now() + 1,
        role: "assistant",
        content: `⚠️ Connection Error: Is the Brain Service running? (python main.py)\n\nDetails: ${err.message}`,
        timestamp: new Date(),
        isError: true
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

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(Math.max(textareaRef.current.scrollHeight, 80), 400)}px`;
    }
  }, [input]);

  const currentModel = models.find(m => m.id === selectedModel);

  return (
    <div className="flex h-screen bg-identra-bg text-identra-text-primary font-sans antialiased">
      
      {/* Left Sidebar */}
      <aside className="w-14 bg-identra-surface/80 border-r border-identra-divider flex flex-col items-center py-4 gap-1 shrink-0 shadow-soft">
        <button className="button-glow p-2.5 rounded-lg transition-all hover:text-identra-text-primary text-identra-text-tertiary">
          <User className="w-5 h-5" />
        </button>
        <div className="flex-1" />
        <button className="button-glow p-2.5 rounded-lg transition-all hover:text-identra-text-primary text-identra-text-tertiary">
          <Settings className="w-5 h-5" />
        </button>
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col min-w-0 border-r border-identra-divider shadow-soft relative overflow-hidden">
        
        {/* Messages List */}
        <div className="flex-1 overflow-y-auto px-8 py-8 space-y-6">
          {messages.length === 0 ? (
            <div className="flex flex-col h-full items-center justify-center opacity-70">
               <Brain className="w-16 h-16 text-identra-text-tertiary mb-4 animate-pulse" />
               <h2 className="text-2xl font-bold tracking-tight text-identra-text-primary">IDENTRA BRAIN</h2>
               <p className="text-sm text-identra-text-tertiary mt-2">RAG Memory System Online</p>
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className="w-[70%] flex flex-col gap-2">
                  <div className={`px-5 py-4 rounded-xl shadow-soft transition-all ${
                    msg.role === 'user' 
                      ? 'bg-identra-surface-elevated border border-identra-border text-identra-text-primary ml-auto' 
                      : 'bg-identra-surface border border-identra-border-subtle text-identra-text-primary mr-auto'
                  }`}>
                     {/* RAG Context Indicator (Only for Assistant) */}
                     {msg.role === 'assistant' && msg.memoryDepth > 0 && (
                        <div className="flex items-center gap-2 mb-2 pb-2 border-b border-identra-border-subtle/50">
                           <Database className="w-3 h-3 text-emerald-400" />
                           <span className="text-[10px] text-emerald-400 font-medium tracking-wide">
                             RECALLED {msg.memoryDepth} MEMORIES
                           </span>
                        </div>
                     )}
                     
                    <p className="text-sm leading-7 whitespace-pre-wrap">{msg.content}</p>
                  </div>
                  <div className={`flex items-center gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <span className="text-[10px] text-identra-text-muted opacity-60">
                      {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
          
          {isProcessing && (
            <div className="flex justify-start w-full">
               <div className="flex items-center gap-3 px-4 py-3 bg-identra-surface/50 rounded-lg animate-pulse">
                  <Brain className="w-4 h-4 text-identra-text-tertiary animate-bounce" />
                  <span className="text-xs text-identra-text-tertiary">Accessing Neural Memory...</span>
               </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="max-w-4xl mx-auto w-full px-6 pb-6 pt-2">
           <div className="relative group">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-identra-primary/20 to-purple-500/20 rounded-xl blur opacity-20 group-hover:opacity-40 transition duration-500"></div>
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="Ask the Brain..."
                className="relative w-full bg-identra-surface border border-identra-border-subtle focus:border-identra-primary/50 rounded-xl px-5 py-4 pr-14 text-sm text-identra-text-primary placeholder:text-identra-text-tertiary outline-none shadow-soft focus:shadow-glow transition-all resize-none"
                disabled={isProcessing}
                style={{ minHeight: '60px', maxHeight: '200px' }}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isProcessing}
                className="absolute right-3 bottom-3 p-2 text-identra-text-tertiary hover:text-white bg-identra-surface-elevated hover:bg-identra-primary rounded-lg transition-all shadow-sm hover:shadow-glow disabled:opacity-50"
              >
                <Send className="w-5 h-5" />
              </button>
           </div>
           <div className="flex justify-center mt-3 gap-4">
              <div className="flex items-center gap-1.5">
                 <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
                 <span className="text-[10px] text-identra-text-tertiary font-medium tracking-wider">BRAIN ONLINE</span>
              </div>
              <div className="flex items-center gap-1.5">
                 <Database className="w-3 h-3 text-identra-text-tertiary" />
                 <span className="text-[10px] text-identra-text-tertiary font-medium tracking-wider">MEMORY ACTIVE</span>
              </div>
           </div>
        </div>

      </main>
    </div>
  );
}