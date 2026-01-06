use std::sync::Mutex;
use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum VaultStatus {
    Locked,
    Unlocked,
    Syncing,
    Offline,
}

#[derive(Debug, Serialize, Clone)]
pub struct EnclaveMetrics {
    pub cpu_usage: f32,
    pub memory_encrypted: usize,
    pub active_keys: u32,
}

pub struct NexusState {
    pub status: Mutex<VaultStatus>,
    pub active_identity: Mutex<Option<String>>,
    pub metrics: Mutex<EnclaveMetrics>,
}

impl NexusState {
    pub fn new() -> Self {
        Self {
            status: Mutex::new(VaultStatus::Locked),
            // Default to my admin identity for dev
            active_identity: Mutex::new(Some("manish.Admin".to_string())),
            metrics: Mutex::new(EnclaveMetrics {
                cpu_usage: 0.0,
                memory_encrypted: 0,
                active_keys: 0,
            }),
        }
    }
}