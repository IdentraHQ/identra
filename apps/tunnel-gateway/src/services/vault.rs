use identra_proto::vault::{
    vault_service_server::{VaultService, VaultServiceServer},
    StoreKeyRequest, StoreKeyResponse,
    RetrieveKeyRequest, RetrieveKeyResponse,
    DeleteKeyRequest, DeleteKeyResponse,
    ListKeysRequest, ListKeysResponse,
    KeyExistsRequest, KeyExistsResponse,
};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tonic::{Request, Response, Status};

#[derive(Clone)]
struct StoredKey {
    data: Vec<u8>,
    metadata: HashMap<String, String>,
}

pub struct VaultServiceImpl {
    // In-memory store for MVP (should connect to vault-daemon via IPC)
    keys: Arc<RwLock<HashMap<String, StoredKey>>>,
}

impl VaultServiceImpl {
    pub fn new() -> Self {
        Self {
            keys: Arc::new(RwLock::new(HashMap::new())),
        }
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
        
        let stored_key = StoredKey {
            data: req.key_data,
            metadata: req.metadata,
        };
        
        let mut keys = self.keys.write().await;
        keys.insert(req.key_id.clone(), stored_key);
        
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
        
        let keys = self.keys.read().await;
        let stored_key = keys
            .get(&req.key_id)
            .ok_or_else(|| Status::not_found(format!("Key '{}' not found", req.key_id)))?;
        
        tracing::info!("Retrieved key: {}", req.key_id);
        
        Ok(Response::new(RetrieveKeyResponse {
            key_data: stored_key.data.clone(),
            metadata: stored_key.metadata.clone(),
            created_at: None, // TODO: Add timestamp tracking
        }))
    }
    
    async fn delete_key(
        &self,
        request: Request<DeleteKeyRequest>,
    ) -> Result<Response<DeleteKeyResponse>, Status> {
        let req = request.into_inner();
        
        let mut keys = self.keys.write().await;
        let existed = keys.remove(&req.key_id).is_some();
        
        if existed {
            tracing::info!("Deleted key: {}", req.key_id);
            Ok(Response::new(DeleteKeyResponse {
                success: true,
                message: format!("Key '{}' deleted successfully", req.key_id),
            }))
        } else {
            Ok(Response::new(DeleteKeyResponse {
                success: false,
                message: format!("Key '{}' not found", req.key_id),
            }))
        }
    }
    
    async fn list_keys(
        &self,
        _request: Request<ListKeysRequest>,
    ) -> Result<Response<ListKeysResponse>, Status> {
        let keys = self.keys.read().await;
        let key_ids: Vec<String> = keys.keys().cloned().collect();
        
        tracing::info!("Listed {} keys", key_ids.len());
        
        Ok(Response::new(ListKeysResponse {
            key_ids,
            next_page_token: String::new(), // TODO: Implement pagination
        }))
    }
    
    async fn key_exists(
        &self,
        request: Request<KeyExistsRequest>,
    ) -> Result<Response<KeyExistsResponse>, Status> {
        let req = request.into_inner();
        
        let keys = self.keys.read().await;
        let exists = keys.contains_key(&req.key_id);
        
        Ok(Response::new(KeyExistsResponse { exists }))
    }
}

impl Default for VaultServiceImpl {
    fn default() -> Self {
        Self::new()
    }
}
