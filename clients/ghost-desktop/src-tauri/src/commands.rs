use crate::state::{NexusState, VaultStatus};
use identra_crypto::MemoryVault; 
use tauri::{AppHandle, Manager, State};
use std::path::PathBuf;
use std::fs;
use aes_gcm::{Aes256Gcm, Key}; // Removed unused KeyInit
use fastembed::{TextEmbedding, InitOptions, EmbeddingModel};
use std::sync::Mutex;

// --- Data Models ---

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