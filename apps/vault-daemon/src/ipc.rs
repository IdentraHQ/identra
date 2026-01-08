use crate::error::{Result, VaultError};
use crate::keychain::{KeyStorage, create_key_storage};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;
use interprocess::local_socket::{
    tokio::prelude::*,
    GenericNamespaced, ListenerOptions, ToNsName,
};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};

/// IPC pipe name
#[cfg(windows)]
const PIPE_NAME: &str = "@identra-vault";

#[cfg(unix)]
const PIPE_NAME: &str = "/tmp/identra-vault.sock";

/// IPC message types
#[derive(Debug, Serialize, Deserialize)]
pub enum VaultRequest {
    StoreKey { key_id: String, key_data: Vec<u8> },
    RetrieveKey { key_id: String },
    DeleteKey { key_id: String },
    KeyExists { key_id: String },
    Ping,
    Shutdown,
}

#[derive(Debug, Serialize, Deserialize)]
pub enum VaultResponse {
    Success,
    KeyData(Vec<u8>),
    Exists(bool),
    Error(String),
    Pong,
    ShuttingDown,
}

/// Vault server handling IPC communication
pub struct VaultServer {
    keychain: Arc<Box<dyn KeyStorage>>,
    state: Arc<RwLock<VaultState>>,
}

struct VaultState {
    initialized: bool,
    active_connections: usize,
}

impl VaultServer {
    pub fn new() -> Self {
        let keychain = create_key_storage();
        
        Self {
            keychain: Arc::new(keychain),
            state: Arc::new(RwLock::new(VaultState {
                initialized: false,
                active_connections: 0,
            })),
        }
    }
    
    pub async fn start(&self) -> Result<()> {
        println!("🔌 Starting IPC server on: {}", PIPE_NAME);
        
        // Create listener
        let name = PIPE_NAME.to_ns_name::<GenericNamespaced>()
            .map_err(|e| VaultError::Ipc(format!("Invalid pipe name: {}", e)))?;
        
        let listener = ListenerOptions::new()
            .name(name)
            .create_tokio()
            .map_err(|e| VaultError::Ipc(format!("Failed to create IPC listener: {}", e)))?;
        
        {
            let mut state = self.state.write().await;
            state.initialized = true;
        }
        
        println!("✅ IPC server ready, waiting for connections...");
        
        // Accept connections in a loop
        loop {
            match listener.accept().await {
                Ok(stream) => {
                    println!("📥 New IPC connection accepted");
                    
                    // Increment connection counter
                    {
                        let mut state = self.state.write().await;
                        state.active_connections += 1;
                    }
                    
                    // Handle connection in a separate task
                    let keychain = Arc::clone(&self.keychain);
                    let state = Arc::clone(&self.state);
                    
                    tokio::spawn(async move {
                        if let Err(e) = Self::handle_connection(stream, keychain, state.clone()).await {
                            eprintln!("❌ Connection error: {}", e);
                        }
                    });
                }
                Err(e) => {
                    eprintln!("❌ Failed to accept connection: {}", e);
                    break;
                }
            }
        }
        
        Ok(())
    }
    
    async fn handle_connection(
        stream: interprocess::local_socket::tokio::Stream,
        keychain: Arc<Box<dyn KeyStorage>>,
        state: Arc<RwLock<VaultState>>,
    ) -> Result<()> {
        let (reader, mut writer) = tokio::io::split(stream);
        let mut buf_reader = BufReader::new(reader);
        let mut line = String::new();
        
        loop {
            line.clear();
            
            match buf_reader.read_line(&mut line).await {
                Ok(0) => {
                    // Connection closed
                    println!("📤 Client disconnected");
                    break;
                }
                Ok(_) => {
                    // Parse request
                    let request: VaultRequest = match serde_json::from_str(&line) {
                        Ok(req) => req,
                        Err(e) => {
                            let error_response = VaultResponse::Error(
                                format!("Invalid request format: {}", e)
                            );
                            let response_json = serde_json::to_string(&error_response).unwrap();
                            writer.write_all(response_json.as_bytes()).await
                                .map_err(|e| VaultError::Io(e))?;
                            writer.write_all(b"\n").await
                                .map_err(|e| VaultError::Io(e))?;
                            writer.flush().await
                                .map_err(|e| VaultError::Io(e))?;
                            continue;
                        }
                    };
                    
                    // Handle request
                    let response = Self::handle_request(request, &keychain).await;
                    
                    // Send response
                    let response_json = serde_json::to_string(&response)
                        .map_err(|e| VaultError::Serialization(e))?;
                    
                    writer.write_all(response_json.as_bytes()).await
                        .map_err(|e| VaultError::Io(e))?;
                    writer.write_all(b"\n").await
                        .map_err(|e| VaultError::Io(e))?;
                    writer.flush().await
                        .map_err(|e| VaultError::Io(e))?;
                    
                    // Check for shutdown
                    if matches!(response, VaultResponse::ShuttingDown) {
                        break;
                    }
                }
                Err(e) => {
                    eprintln!("❌ Read error: {}", e);
                    break;
                }
            }
        }
        
        // Decrement connection counter
        {
            let mut state_guard = state.write().await;
            state_guard.active_connections = state_guard.active_connections.saturating_sub(1);
        }
        
        Ok(())
    }
    
    async fn handle_request(
        request: VaultRequest,
        keychain: &Arc<Box<dyn KeyStorage>>,
    ) -> VaultResponse {
        match request {
            VaultRequest::Ping => {
                println!("🏓 Ping received");
                VaultResponse::Pong
            }
            VaultRequest::StoreKey { key_id, key_data } => {
                println!("📝 Storing key: {}", key_id);
                match keychain.store_key(&key_id, &key_data) {
                    Ok(_) => VaultResponse::Success,
                    Err(e) => VaultResponse::Error(format!("Failed to store key: {}", e)),
                }
            }
            VaultRequest::RetrieveKey { key_id } => {
                println!("🔍 Retrieving key: {}", key_id);
                match keychain.retrieve_key(&key_id) {
                    Ok(data) => VaultResponse::KeyData(data),
                    Err(e) => VaultResponse::Error(format!("Failed to retrieve key: {}", e)),
                }
            }
            VaultRequest::DeleteKey { key_id } => {
                println!("🗑️ Deleting key: {}", key_id);
                match keychain.delete_key(&key_id) {
                    Ok(_) => VaultResponse::Success,
                    Err(e) => VaultResponse::Error(format!("Failed to delete key: {}", e)),
                }
            }
            VaultRequest::KeyExists { key_id } => {
                let exists = keychain.key_exists(&key_id);
                VaultResponse::Exists(exists)
            }
            VaultRequest::Shutdown => {
                println!("🛑 Shutdown request received");
                VaultResponse::ShuttingDown
            }
        }
    }
    
    pub async fn get_active_connections(&self) -> usize {
        self.state.read().await.active_connections
    }
}

impl Default for VaultServer {
    fn default() -> Self {
        Self::new()
    }
}
