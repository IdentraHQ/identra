use std::sync::Mutex;
use aes_gcm::{Key, Aes256Gcm};

#[derive(Debug, Clone, serde::Serialize, PartialEq)]
pub enum VaultStatus {
    Locked,
    Unlocked,
    Syncing,
    Offline,
}

pub struct NexusState {
    pub status: Mutex<VaultStatus>,
    pub active_identity: Mutex<Option<String>>,
    pub metrics: Mutex<VaultMetrics>,
    // This holds the session key in RAM
    pub session_key: Mutex<Option<Key<Aes256Gcm>>>, 
}

#[derive(Debug, Clone, Default)]
pub struct VaultMetrics {
    pub memory_encrypted: usize,
    pub active_tunnels: u32,
}

impl NexusState {
    pub fn new() -> Self {
        Self {
            status: Mutex::new(VaultStatus::Locked),
            active_identity: Mutex::new(None),
            metrics: Mutex::new(VaultMetrics::default()),
            session_key: Mutex::new(None),
        }
    }
}