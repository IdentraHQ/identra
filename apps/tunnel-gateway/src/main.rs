mod error;
mod services;

use error::Result;
use services::{HealthService, VaultServiceImpl};
use tonic::transport::Server;
use tracing::{info, Level};
use tracing_subscriber;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_max_level(Level::INFO)
        .init();
    
    info!("🚀 Identra Tunnel Gateway starting...");
    
    let addr = "[::1]:50051".parse().unwrap();
    info!("📡 gRPC server listening on {}", addr);
    
    // Initialize services
    let health_service = HealthService::new().into_server();
    let vault_service = VaultServiceImpl::new().into_server();
    
    info!("✅ Services initialized:");
    info!("   - Health Service");
    info!("   - Vault Service");
    
    // Start gRPC server
    Server::builder()
        .add_service(health_service)
        .add_service(vault_service)
        .serve(addr)
        .await?;
    
    Ok(())
}
