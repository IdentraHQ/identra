use identra_proto::vault::{
    vault_service_server::{VaultService, VaultServiceServer},
    StoreKeyRequest, StoreKeyResponse,
    RetrieveKeyRequest, RetrieveKeyResponse,
    DeleteKeyRequest, DeleteKeyResponse,
    ListKeysRequest, ListKeysResponse,
    KeyExistsRequest, KeyExistsResponse,
};
use crate::ipc_client::VaultClient;
use tonic::{Request, Response, Status};

pub struct VaultServiceImpl;

impl VaultServiceImpl {
    pub fn new() -> Self {
        Self
    }
    
    pub fn into_server(self) -> VaultServiceServer<Self> {
        VaultServiceServer::new(self)
    }
}

#[tonic::async_trait]
impl VaultService for VaultServiceImpl {
    async fn store_key(
        &self,
        request: Request<StoreKeyRequest>,
    ) -> Result<Response<StoreKeyResponse>, Status> {
        let req = request.into_inner();
        
        let mut client = VaultClient::connect()
            .await
            .map_err(|e| Status::unavailable(format!("Vault daemon not available: {}", e)))?;
        
        client.store_key(req.key_id.clone(), req.key_data)
            .await
            .map_err(|e| Status::internal(format!("Failed to store key: {}", e)))?;
        
        tracing::info!("Stored key: {}", req.key_id);
        
        Ok(Response::new(StoreKeyResponse {
            success: true,
            message: format!("Key '{}' stored successfully", req.key_id),
        }))
    }
    
    async fn retrieve_key(
        &self,
        request: Request<RetrieveKeyRequest>,
    ) -> Result<Response<RetrieveKeyResponse>, Status> {
        let req = request.into_inner();
        
        let mut client = VaultClient::connect()
            .await
            .map_err(|e| Status::unavailable(format!("Vault daemon not available: {}", e)))?;
        
        let key_data = client.retrieve_key(req.key_id.clone())
            .await
            .map_err(|e| Status::not_found(format!("Key not found: {}", e)))?;
        
        tracing::info!("Retrieved key: {}", req.key_id);
        
        Ok(Response::new(RetrieveKeyResponse {
            key_data,
            metadata: std::collections::HashMap::new(), // TODO: Store metadata in vault-daemon
            created_at: None, // TODO: Add timestamp tracking in vault-daemon
        }))
    }
    
    async fn delete_key(
        &self,
        request: Request<DeleteKeyRequest>,
    ) -> Result<Response<DeleteKeyResponse>, Status> {
        let req = request.into_inner();
        
        let mut client = VaultClient::connect()
            .await
            .map_err(|e| Status::unavailable(format!("Vault daemon not available: {}", e)))?;
        
        client.delete_key(req.key_id.clone())
            .await
            .map_err(|e| Status::internal(format!("Failed to delete key: {}", e)))?;
        
        tracing::info!("Deleted key: {}", req.key_id);
        
        Ok(Response::new(DeleteKeyResponse {
            success: true,
            message: format!("Key '{}' deleted successfully", req.key_id),
        }))
    }
    
    async fn list_keys(
        &self,
        _request: Request<ListKeysRequest>,
    ) -> Result<Response<ListKeysResponse>, Status> {
        // TODO: Implement list_keys in vault-daemon IPC protocol
        // For now, return empty list as this requires vault-daemon protocol update
        tracing::warn!("list_keys not yet implemented in vault-daemon");
        
        Ok(Response::new(ListKeysResponse {
            key_ids: vec![],
            next_page_token: String::new(),
        }))
    }
    
    async fn key_exists(
        &self,
        request: Request<KeyExistsRequest>,
    ) -> Result<Response<KeyExistsResponse>, Status> {
        let req = request.into_inner();
        
        let mut client = VaultClient::connect()
            .await
            .map_err(|e| Status::unavailable(format!("Vault daemon not available: {}", e)))?;
        
        let exists = client.key_exists(req.key_id.clone())
            .await
            .map_err(|e| Status::internal(format!("Failed to check key existence: {}", e)))?;
        
        Ok(Response::new(KeyExistsResponse { exists }))
    }
}

impl Default for VaultServiceImpl {
    fn default() -> Self {
        Self::new()
    }
}
