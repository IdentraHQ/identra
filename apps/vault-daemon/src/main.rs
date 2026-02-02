use anyhow::Result;
use tonic::transport::Server;
use std::net::SocketAddr;

// Import gRPC service
use identra_proto::memory::memory_service_server::MemoryServiceServer;
use vault_daemon::grpc_service::MemoryServiceImpl;

#[tokio::main]
async fn main() -> Result<()> {
    println!("🔐 Identra Vault Daemon starting...");
    println!("📍 Local secure storage initialized");
    println!("🔑 OS Keychain integration active");
    
    // Initialize gRPC Memory Service
    let memory_service = MemoryServiceImpl::new()
        .map_err(|e| anyhow::anyhow!("Failed to initialize memory service: {}", e))?;
    
    // gRPC server address
    let addr: SocketAddr = "127.0.0.1:50051".parse()?;
    println!("🚀 gRPC server starting on {}", addr);
    
    // Start gRPC server
    tokio::select! {
        result = Server::builder()
            .add_service(MemoryServiceServer::new(memory_service))
            .serve(addr) => {
            if let Err(e) = result {
                eprintln!("❌ gRPC Server error: {}", e);
                return Err(e.into());
            }
        }
        _ = tokio::signal::ctrl_c() => {
            println!("\n🛑 Shutdown signal received");
        }
    }
    
    println!("🛑 Shutting down Vault Daemon...");
    Ok(())
}
