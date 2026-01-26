use crate::state::{NexusState, VaultStatus};
use identra_crypto::MemoryVault; 
use tauri::{AppHandle, Manager, State};
use std::path::PathBuf;
use std::fs;
use aes_gcm::{Aes256Gcm, Key}; // Removed unused KeyInit
use fastembed::{TextEmbedding, InitOptions, EmbeddingModel};
use std::sync::Mutex;
use std::collections::HashMap;

// --- Helper Functions ---

fn get_env_or(key: &str, default: &str) -> String {
    std::env::var(key).unwrap_or_else(|_| default.to_string())
}

#[allow(dead_code)]
fn get_context_limit() -> usize {
    std::env::var("CHAT_CONTEXT_LIMIT")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(10)
}

// --- Data Models ---

#[derive(serde::Deserialize, serde::Serialize, Clone)]
pub struct ChatMessage {
    pub role: String,  // "user" or "assistant"
    pub content: String,
    pub timestamp: i64,
}

#[derive(serde::Serialize)]
pub struct ChatResponse {
    pub message: String,
    pub model: String,
    pub conversation_id: Option<String>,
}

#[derive(serde::Serialize)]
pub struct SystemStatusResponse {
    pub vault_status: VaultStatus,
    pub active_identity: Option<String>,
    pub enclave_connection: bool,
    pub security_level: String,
}

#[derive(serde::Serialize)]
pub struct ConversationItem {
    pub id: String,
    pub content: String,
    pub timestamp: i64,
}

// --- AI State (For Local Embeddings) ---

pub struct AIState {
    pub model: Mutex<TextEmbedding>,
}

impl AIState {
    pub fn new() -> Self {
        // Initialize the model. This might take a moment on first load.
        let model = TextEmbedding::try_new(InitOptions::new(EmbeddingModel::AllMiniLML6V2))
            .expect("Failed to load local AI in Frontend");
        Self { model: Mutex::new(model) }
    }
}

// --- System Commands ---

#[tauri::command]
pub async fn get_system_status(state: State<'_, NexusState>) -> Result<SystemStatusResponse, String> {
    let status = state.status.lock().map_err(|_| "State poisoned")?.clone();
    let identity = state.active_identity.lock().map_err(|_| "Identity poisoned")?.clone();
    
    Ok(SystemStatusResponse {
        vault_status: status,
        active_identity: identity,
        enclave_connection: true, 
        security_level: "MAXIMUM".to_string(),
    })
}

#[tauri::command]
pub async fn toggle_launcher(app: AppHandle) -> Result<(), String> {
    let launcher = app.get_webview_window("launcher").ok_or("Launcher window not found")?;
    if launcher.is_visible().unwrap_or(false) {
        launcher.hide().map_err(|e| e.to_string())?;
    } else {
        launcher.show().map_err(|e| e.to_string())?;
        launcher.set_focus().map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tauri::command]
pub async fn toggle_main_window(app: AppHandle) -> Result<(), String> {
    let main = app.get_webview_window("main").ok_or("Main window not found")?;
    if main.is_visible().unwrap_or(false) {
        main.hide().map_err(|e| e.to_string())?;
    } else {
        main.show().map_err(|e| e.to_string())?;
        main.set_focus().map_err(|e| e.to_string())?;
    }
    Ok(())
}

// --- Security & Vault Commands ---

fn get_session_key_path() -> PathBuf {
    let mut path = std::env::temp_dir();
    path.push("identra_session_key.bin");
    path
}

#[tauri::command]
pub async fn initialize_session(state: State<'_, NexusState>) -> Result<String, String> {
    let key_path = get_session_key_path();
    
    let key = if key_path.exists() {
        match fs::read(&key_path) {
            Ok(bytes) if bytes.len() == 32 => {
                println!("[NEXUS] Loaded existing session key from disk");
                Key::<Aes256Gcm>::clone_from_slice(&bytes)
            }
            _ => {
                let new_key = MemoryVault::generate_key();
                let _ = fs::write(&key_path, new_key.as_slice());
                new_key
            }
        }
    } else {
        let new_key = MemoryVault::generate_key();
        let _ = fs::write(&key_path, new_key.as_slice());
        new_key
    };

    *state.session_key.lock().map_err(|_| "Key poisoned")? = Some(key);
    *state.status.lock().map_err(|_| "Status poisoned")? = VaultStatus::Unlocked;

    println!("[NEXUS] Session Initialized. Vault UNLOCKED.");
    Ok("Vault Unlocked".to_string())
}

#[tauri::command]
pub async fn vault_memory(state: State<'_, NexusState>, content: String) -> Result<String, String> {
    if content.trim().is_empty() { return Err("Payload empty.".to_string()); }

    let session_key = {
        let key_guard = state.session_key.lock().map_err(|_| "Key poisoned")?;
        match key_guard.as_ref() {
            Some(k) => k.clone(),
            None => return Err("VAULT_LOCKED: Please initialize session first.".to_string()),
        }
    };

    // Encrypt content
    let encrypted_blob = MemoryVault::lock(&content, &session_key)
        .map_err(|e| format!("Crypto Error: {}", e))?;

    // Store in DB
    let mut client = crate::grpc_client::GrpcClient::connect()
        .await
        .map_err(|e| format!("Failed to connect to gateway: {}", e))?;
    
    let metadata = std::collections::HashMap::from([
        ("encrypted".to_string(), "true".to_string()),
        ("timestamp".to_string(), chrono::Utc::now().to_rfc3339()),
    ]);
    
    let memory_id = client
        .store_memory(encrypted_blob.clone(), metadata, vec![])
        .await
        .map_err(|e| format!("Failed to store memory: {}", e))?;

    // Update metrics
    {
        let mut metrics = state.metrics.lock().map_err(|_| "Metrics poisoned")?;
        metrics.memory_encrypted += content.len();
    }
    
    println!("[NEXUS] Vaulted (ID: {})", memory_id);
    Ok(format!("Stored successfully (ID: {})", memory_id))
}

#[tauri::command]
pub async fn decrypt_memory(state: State<'_, NexusState>, encrypted_val: String) -> Result<String, String> {
    let key_guard = state.session_key.lock().map_err(|_| "Key poisoned")?;
    let session_key = match &*key_guard {
        Some(k) => k,
        None => return Err("VAULT_LOCKED".to_string()),
    };

    let plaintext = MemoryVault::open(&encrypted_val, session_key)
        .map_err(|e| format!("Decryption Failed: {}", e))?;

    Ok(plaintext)
}

#[tauri::command]
pub async fn chat_with_ai(
    state: State<'_, NexusState>,
    message: String,
    model: String,
    conversation_history: Vec<ChatMessage>,
) -> Result<ChatResponse, String> {
    if message.trim().is_empty() {
        return Err("Message cannot be empty".to_string());
    }

    // Get API key from environment variable based on model
    let api_key = match model.as_str() {
        "claude" => get_env_or("ANTHROPIC_API_KEY", "demo-key"),
        "gpt" => get_env_or("OPENAI_API_KEY", "demo-key"),
        "gemini" => get_env_or("GOOGLE_API_KEY", "demo-key"),
        _ => return Err("Unsupported model".to_string()),
    };

    // For demo purposes, if no API key is set, return a mock response
    if api_key == "demo-key" {
        println!("[CHAT] Demo mode: No API key found for model: {}", model);
        let response_text = format!(
            "[Demo Response from {}] I received your message: '{}'. To enable real AI responses, please set the appropriate API key environment variable (ANTHROPIC_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY).",
            model, message
        );
        
        // Store both user message and response
        let _ = store_chat_interaction(&state, &message, &response_text, &model).await;
        
        return Ok(ChatResponse {
            message: response_text,
            model: model.clone(),
            conversation_id: None,
        });
    }

    // Call the appropriate LLM API
    let response_text = match model.as_str() {
        "claude" => call_claude_api(&api_key, &message, &conversation_history).await?,
        "gpt" => call_openai_api(&api_key, &message, &conversation_history).await?,
        "gemini" => call_gemini_api(&api_key, &message, &conversation_history).await?,
        _ => return Err("Unsupported model".to_string()),
    };

    // Store the conversation in encrypted vault
    let _ = store_chat_interaction(&state, &message, &response_text, &model).await;

    Ok(ChatResponse {
        message: response_text,
        model: model.clone(),
        conversation_id: None,
    })
}

async fn store_chat_interaction(
    state: &State<'_, NexusState>,
    user_message: &str,
    ai_response: &str,
    model: &str,
) -> Result<(), String> {
    let session_key = {
        let key_guard = state.session_key.lock().map_err(|_| "Key poisoned")?;
        match key_guard.as_ref() {
            Some(k) => k.clone(),
            None => return Ok(()), // Skip storage if vault is locked
        }
    };

    // Create conversation record
    let conversation = serde_json::json!({
        "user": user_message,
        "assistant": ai_response,
        "model": model,
        "timestamp": chrono::Utc::now().to_rfc3339(),
    });

    let conversation_str = serde_json::to_string(&conversation)
        .map_err(|e| format!("JSON error: {}", e))?;

    // Encrypt and store
    let encrypted_blob = MemoryVault::lock(&conversation_str, &session_key)
        .map_err(|e| format!("Encryption error: {}", e))?;

    let mut client = crate::grpc_client::GrpcClient::connect()
        .await
        .map_err(|e| format!("Failed to connect: {}", e))?;

    let metadata = HashMap::from([
        ("type".to_string(), "conversation".to_string()),
        ("model".to_string(), model.to_string()),
        ("timestamp".to_string(), chrono::Utc::now().to_rfc3339()),
    ]);

    let _ = client.store_memory(encrypted_blob, metadata, vec!["chat".to_string()])
        .await
        .map_err(|e| format!("Storage error: {}", e))?;

    Ok(())
}

async fn call_claude_api(
    api_key: &str,
    message: &str,
    history: &[ChatMessage],
) -> Result<String, String> {
    let client = reqwest::Client::new();
    
    let mut messages = vec![];
    for msg in history {
        messages.push(serde_json::json!({
            "role": msg.role,
            "content": msg.content,
        }));
    }
    messages.push(serde_json::json!({
        "role": "user",
        "content": message,
    }));

    let model = get_env_or("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022");
    let max_tokens: i32 = get_env_or("ANTHROPIC_MAX_TOKENS", "1024").parse().unwrap_or(1024);
    
    let body = serde_json::json!({
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    });

    let api_url = get_env_or("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages");
    let api_version = get_env_or("ANTHROPIC_API_VERSION", "2023-06-01");
    
    let response = client
        .post(&api_url)
        .header("x-api-key", api_key)
        .header("anthropic-version", api_version)
        .header("content-type", "application/json")
        .json(&body)
        .send()
        .await
        .map_err(|e| format!("API request failed: {}", e))?;

    let json: serde_json::Value = response
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    json["content"][0]["text"]
        .as_str()
        .ok_or_else(|| "Invalid response format".to_string())
        .map(|s| s.to_string())
}

async fn call_openai_api(
    api_key: &str,
    message: &str,
    history: &[ChatMessage],
) -> Result<String, String> {
    let client = reqwest::Client::new();
    
    let mut messages = vec![];
    for msg in history {
        messages.push(serde_json::json!({
            "role": msg.role,
            "content": msg.content,
        }));
    }
    messages.push(serde_json::json!({
        "role": "user",
        "content": message,
    }));

    let model = get_env_or("OPENAI_MODEL", "gpt-4o");
    let max_tokens: i32 = get_env_or("OPENAI_MAX_TOKENS", "1024").parse().unwrap_or(1024);
    
    let body = serde_json::json!({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    });

    let api_url = get_env_or("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions");
    
    let response = client
        .post(&api_url)
        .header("Authorization", format!("Bearer {}", api_key))
        .header("content-type", "application/json")
        .json(&body)
        .send()
        .await
        .map_err(|e| format!("API request failed: {}", e))?;

    let json: serde_json::Value = response
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    json["choices"][0]["message"]["content"]
        .as_str()
        .ok_or_else(|| "Invalid response format".to_string())
        .map(|s| s.to_string())
}

async fn call_gemini_api(
    api_key: &str,
    message: &str,
    history: &[ChatMessage],
) -> Result<String, String> {
    let client = reqwest::Client::new();
    
    let mut contents = vec![];
    for msg in history {
        let role = if msg.role == "assistant" { "model" } else { "user" };
        contents.push(serde_json::json!({
            "role": role,
            "parts": [{ "text": msg.content }],
        }));
    }
    contents.push(serde_json::json!({
        "role": "user",
        "parts": [{ "text": message }],
    }));

    let max_tokens: i32 = get_env_or("GEMINI_MAX_TOKENS", "1024").parse().unwrap_or(1024);
    
    let body = serde_json::json!({
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": max_tokens,
        },
    });

    let base_url = get_env_or("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/models");
    let model = get_env_or("GEMINI_MODEL", "gemini-1.5-pro");
    let url = format!("{}/{}:generateContent?key={}", base_url, model, api_key);

    let response = client
        .post(&url)
        .header("content-type", "application/json")
        .json(&body)
        .send()
        .await
        .map_err(|e| format!("API request failed: {}", e))?;

    let json: serde_json::Value = response
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    json["candidates"][0]["content"]["parts"][0]["text"]
        .as_str()
        .ok_or_else(|| "Invalid response format".to_string())
        .map(|s| s.to_string())
}

#[tauri::command]
pub async fn query_history(limit: i32) -> Result<Vec<ConversationItem>, String> {
    let mut client = crate::grpc_client::GrpcClient::connect()
        .await
        .map_err(|e| format!("Failed to connect: {}", e))?;
    
    // Legacy query: empty string matches everything via ILIKE %%
    let memories = client
        .query_memories("".to_string(), limit)
        .await
        .map_err(|e| format!("Failed to query: {}", e))?;
    
    let items: Vec<ConversationItem> = memories.into_iter()
        .map(|(id, content, timestamp)| ConversationItem { id, content, timestamp })
        .collect();
    
    Ok(items)
}

// --- Auth Commands ---

#[tauri::command]
pub async fn login_user(username: String, password: String) -> Result<String, String> {
    let mut client = crate::grpc_client::GrpcClient::connect()
        .await
        .map_err(|e| format!("Connection failed: {}", e))?;

    let token = client.login(username, password)
        .await
        .map_err(|e| e.to_string())?;

    println!("[AUTH] Login successful");
    Ok(token)
}

#[tauri::command]
pub async fn register_user(username: String, email: String, password: String) -> Result<String, String> {
    let mut client = crate::grpc_client::GrpcClient::connect()
        .await
        .map_err(|e| format!("Connection failed: {}", e))?;

    let user_id = client.register(username, email, password)
        .await
        .map_err(|e| e.to_string())?;

    println!("[AUTH] Registration successful: {}", user_id);
    Ok(user_id)
}

// --- Search & History Commands ---

#[tauri::command]
pub async fn semantic_search(
    ai_state: State<'_, AIState>,
    query: String
) -> Result<Vec<ConversationItem>, String> {
    // 1. Generate Vector Locally
    let embedding = {
        // FIX: model must be mutable for .embed()
        let mut model = ai_state.model.lock().map_err(|_| "AI Busy")?;
        let documents = vec![query];
        let embeddings = model.embed(documents, None).map_err(|e| e.to_string())?;
        embeddings[0].clone()
    };

    // 2. Send to Backend
    let mut client = crate::grpc_client::GrpcClient::connect()
        .await
        .map_err(|e| format!("Connection failed: {}", e))?;

    let results = client.search_memories(embedding, 5, 0.5)
        .await
        .map_err(|e| format!("Search failed: {}", e))?;

    // 3. Format
    let items = results.into_iter().map(|(id, content, score)| {
        ConversationItem {
            id,
            content: format!("(Match: {:.0}%) {}", score * 100.0, content),
            timestamp: 0, 
        }
    }).collect();

    Ok(items)
}

#[tauri::command]
pub async fn fetch_history() -> Result<Vec<ConversationItem>, String> {
    let mut client = crate::grpc_client::GrpcClient::connect()
        .await
        .map_err(|e| format!("Connection failed: {}", e))?;

    let memories = client.get_recent_memories(50)
        .await
        .map_err(|e| e.to_string())?;

    let items = memories.into_iter().map(|(id, content, timestamp)| {
        ConversationItem {
            id,
            content,
            timestamp,
        }
    }).collect();

    Ok(items)
}