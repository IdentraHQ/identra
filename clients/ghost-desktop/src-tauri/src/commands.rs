use crate::state::{NexusState, VaultStatus};
use identra_crypto::MemoryVault; 
use tauri::{AppHandle, Manager, State};

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
    // This looks for the window labeled "launcher" in tauri.conf.json
    let launcher = app.get_webview_window("launcher").ok_or("Launcher window not found in config")?;

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

// --- SECURITY COMMANDS ---

#[tauri::command]
pub async fn initialize_session(state: State<'_, NexusState>) -> Result<String, String> {
    let key = MemoryVault::generate_key();

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

    let key_guard = state.session_key.lock().map_err(|_| "Key poisoned")?;
    let session_key = match &*key_guard {
        Some(k) => k,
        None => return Err("VAULT_LOCKED: Please initialize session first.".to_string()),
    };

    let encrypted_blob = MemoryVault::lock(&content, session_key)
        .map_err(|e| format!("Crypto Error: {}", e))?;

    // Update metrics
    {
        let mut metrics = state.metrics.lock().map_err(|_| "Metrics poisoned")?;
        metrics.memory_encrypted += content.len();
    }
    
    println!("[NEXUS] Vaulted: {}...", &encrypted_blob[0..10]);
    Ok(encrypted_blob)
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