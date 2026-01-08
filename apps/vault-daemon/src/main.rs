use anyhow::Result;
use vault_daemon::VaultServer;

#[tokio::main]
async fn main() -> Result<()> {
    println!("🔐 Identra Vault Daemon starting...");
    println!("📍 Local secure storage initialized");
    println!("🔑 OS Keychain integration active");
    
    // Initialize IPC server
    let server = VaultServer::new();
    
    // Start listening for IPC connections
    // This will block until shutdown signal
    tokio::select! {
        result = server.start() => {
            if let Err(e) = result {
                eprintln!("❌ Server error: {}", e);
            }
        }
        _ = tokio::signal::ctrl_c() => {
            println!("\n🛑 Shutdown signal received");
        }
    }
    
    println!("🛑 Shutting down Vault Daemon...");
    Ok(())
}
