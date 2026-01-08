use thiserror::Error;

#[derive(Error, Debug)]
pub enum VaultError {
    #[error("Keychain error: {0}")]
    Keychain(String),
    
    #[error("Memory lock error: {0}")]
    MemoryLock(String),
    
    #[error("IPC error: {0}")]
    Ipc(String),
    
    #[error("Encryption error: {0}")]
    Encryption(String),
    
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    
    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

pub type Result<T> = std::result::Result<T, VaultError>;
