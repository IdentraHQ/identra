use crate::state::{NexusState, VaultStatus};
use identra_crypto::MemoryVault; 
use tauri::{AppHandle, Manager, State};
use std::path::PathBuf;
use std::fs;
use aes_gcm::{Aes256Gcm, Key, aead::KeyInit};

#[derive(serde::Serialize)]
pub struct SystemStatusResponse {
    pub vault_status: VaultStatus,
    pub active_identity: Option<String>,
    pub enclave_connection: bool,
    pub security_level: String,
}

#[tauri::command]
pub async fn get_system_status(state: State<'_, NexusState>) -> Result<SystemStatusResponse, String> {
    let status = state.status.lock().map_err(|_| "State poisoned")?.clone();
    let identity = state.active_identity.lock().map_err(|_| "Identity poisoned")?.clone();
    
    Ok(SystemStatusResponse {
        vault_status: status,
        active_identity: identity,
        enclave_connection: true, // Mocked for now
        security_level: "MAXIMUM".to_string(),
    })
}

#[tauri::command]
pub async fn toggle_launcher(app: AppHandle) -> Result<(), String> {
    println!("Toggle launcher called");
    // This looks for the window labeled "launcher" in tauri.conf.json
    let launcher = app.get_webview_window("launcher").ok_or("Launcher window not found in config")?;

    let is_visible = launcher.is_visible().unwrap_or(false);
    println!("Launcher is currently visible: {}", is_visible);

    if is_visible {
        println!("Hiding launcher");
        launcher.hide().map_err(|e| e.to_string())?;
    } else {
        println!("Showing launcher");
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

// --- SECURITY COMMANDS ---

fn get_session_key_path() -> PathBuf {
    let mut path = std::env::temp_dir();
    path.push("identra_session_key.bin");
    path
}

#[tauri::command]
pub async fn initialize_session(state: State<'_, NexusState>) -> Result<String, String> {
    let key_path = get_session_key_path();
    
    // Try to load existing session key, or generate a new one
    let key = if key_path.exists() {
        match fs::read(&key_path) {
            Ok(bytes) if bytes.len() == 32 => {
                println!("[NEXUS] Loaded existing session key from disk");
                Key::<Aes256Gcm>::clone_from_slice(&bytes)
            }
            _ => {
                let new_key = MemoryVault::generate_key();
                let _ = fs::write(&key_path, new_key.as_slice());
                println!("[NEXUS] Generated new session key and saved to disk");
                new_key
            }
        }
    } else {
        let new_key = MemoryVault::generate_key();
        let _ = fs::write(&key_path, new_key.as_slice());
        println!("[NEXUS] Generated new session key and saved to disk");
        new_key
    };

    let mut key_store = state.session_key.lock().map_err(|_| "Key poisoned")?;
    *key_store = Some(key);

    let mut status = state.status.lock().map_err(|_| "Status poisoned")?;
    *status = VaultStatus::Unlocked;

    println!("[NEXUS] Session Initialized. Vault UNLOCKED.");
    Ok("Vault Unlocked".to_string())
}

#[tauri::command]
pub async fn vault_memory(state: State<'_, NexusState>, content: String) -> Result<String, String> {
    if content.trim().is_empty() { return Err("Payload empty.".to_string()); }

    // Get session key and drop guard before await
    let session_key = {
        let key_guard = state.session_key.lock().map_err(|_| "Key poisoned")?;
        match key_guard.as_ref() {
            Some(k) => k.clone(),
            None => return Err("VAULT_LOCKED: Please initialize session first.".to_string()),
        }
    };

    // Encrypt content locally
    let encrypted_blob = MemoryVault::lock(&content, &session_key)
        .map_err(|e| format!("Crypto Error: {}", e))?;

    // Store encrypted content in tunnel-gateway database
    let mut client = crate::grpc_client::GrpcClient::connect()
        .await
        .map_err(|e| format!("Failed to connect to tunnel-gateway: {}", e))?;
    
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
    
    println!("[NEXUS] Vaulted & stored in DB (ID: {}): {}...", memory_id, &encrypted_blob[0..10.min(encrypted_blob.len())]);
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
#[derive(serde::Serialize)]
pub struct ConversationItem {
    pub id: String,
    pub content: String,
    pub timestamp: i64,
}

#[tauri::command]
pub async fn query_history(limit: i32) -> Result<Vec<ConversationItem>, String> {
    let mut client = crate::grpc_client::GrpcClient::connect()
        .await
        .map_err(|e| format!("Failed to connect to tunnel-gateway: {}", e))?;
    
    let memories = client
        .query_memories("".to_string(), limit)
        .await
        .map_err(|e| format!("Failed to query memories: {}", e))?;
    
    let items: Vec<ConversationItem> = memories.into_iter()
        .map(|(id, content, timestamp)| ConversationItem {
            id,
            content,
            timestamp,
        })
        .collect();
    
    println!("[NEXUS] Retrieved {} conversation items", items.len());
    Ok(items)
}
