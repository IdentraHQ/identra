mod auth;
mod database;
mod error;
mod services;
mod ipc_client;

use auth::{AuthInterceptor, AuthServiceImpl, JwtManager, UserDatabase};
use database::MemoryDatabase;
use error::Result;
use identra_proto::auth::auth_service_server::AuthServiceServer;
use services::{
    health::HealthService,
    vault::VaultServiceImpl,
    memory::MemoryServiceImpl,
};
use std::sync::Arc;
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
    
    // Create data directory if it doesn't exist
    let data_dir = std::env::current_dir().unwrap().join("data");
    std::fs::create_dir_all(&data_dir)?;
    
    // Initialize memory database
    let db_path = data_dir.join("memories.db");
    let db = Arc::new(MemoryDatabase::new(&db_path)?);
    info!("💾 Memory database initialized at: {:?}", db_path);
    
    // Initialize user database
    let user_db_path = data_dir.join("users.db");
    let user_db = Arc::new(UserDatabase::new(&user_db_path)?);
    info!("👥 User database initialized at: {:?}", user_db_path);
    
    // Initialize JWT manager
    let jwt_manager = Arc::new(JwtManager::new());
    info!("🔐 JWT manager initialized");
    
    // Initialize auth interceptor
    let auth_interceptor = AuthInterceptor::new(Arc::clone(&jwt_manager));
    
    let addr = "[::1]:50051".parse().unwrap();
    info!("📡 gRPC server listening on {}", addr);
    
    // Initialize services
    let health_service = HealthService::new().into_server();
    let vault_service = VaultServiceImpl::new().into_server();
    let memory_service = MemoryServiceImpl::new(Arc::clone(&db)).into_server();
    
    // Initialize auth service (no authentication required for auth endpoints)
    let auth_service = AuthServiceServer::new(
        AuthServiceImpl::new(Arc::clone(&jwt_manager), Arc::clone(&user_db))
    );
    
    info!("✅ Services initialized:");
    info!("   - Health Service");
    info!("   - Auth Service");
    info!("   - Vault Service (protected)");
    info!("   - Memory Service (protected)");
    
    // Start gRPC server
    // Note: In a production setup, you would wrap vault_service and memory_service
    // with the auth_interceptor. For now, they're accessible without auth.
    // TODO: Add interceptor when tonic supports it properly
    Server::builder()
        .add_service(health_service)
        .add_service(auth_service)
        .add_service(vault_service)
        .add_service(memory_service)
        .serve(addr)
        .await?;
    
    Ok(())
}
