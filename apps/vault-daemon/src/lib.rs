// Keychain integration module
pub mod keychain;

// Memory security module
pub mod memory;

// IPC communication module
pub mod ipc;

// Error types
mod error;

pub use error::{VaultError, Result};
pub use keychain::KeyStorage;
pub use memory::SecureMemory;
pub use ipc::VaultServer;
