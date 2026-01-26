use identra_proto::memory::{
    memory_service_server::{MemoryService, MemoryServiceServer},
    Memory, MemoryMatch,
    StoreMemoryRequest, StoreMemoryResponse,
    QueryMemoriesRequest, QueryMemoriesResponse,
    GetMemoryRequest, GetMemoryResponse,
    DeleteMemoryRequest, DeleteMemoryResponse,
    SearchMemoriesRequest, SearchMemoriesResponse,
    GetRecentMemoriesRequest, GetRecentMemoriesResponse,
};
use crate::database::MemoryDatabase;
use std::sync::{Arc, Mutex};
use tonic::{Request, Response, Status};
use uuid::Uuid;
use fastembed::{TextEmbedding, InitOptions, EmbeddingModel};
use std::collections::HashMap;

// Shared model for Database <-> Service communication
#[derive(Debug, Clone)]
pub struct MemoryModel {
    pub id: String,
    pub content: String,
    pub metadata: HashMap<String, String>,
    pub embedding: Vec<f32>,
    pub tags: Vec<String>,
    pub created_at: i64,
    pub updated_at: i64,
}

pub struct MemoryServiceImpl {
    db: Arc<MemoryDatabase>,
    embedder: Arc<Mutex<TextEmbedding>>, 
}

impl MemoryServiceImpl {
    pub fn new(db: Arc<MemoryDatabase>) -> Self {
        tracing::info!("🧠 Initializing Neural Engine...");
        
        let options = InitOptions::new(EmbeddingModel::AllMiniLML6V2)
            .with_show_download_progress(true);

        let embedder = TextEmbedding::try_new(options)
            .expect("Failed to load local embedding model");

        Self { 
            db, 
            embedder: Arc::new(Mutex::new(embedder)) 
        }
    }
    
    pub fn into_server(self) -> MemoryServiceServer<Self> {
        MemoryServiceServer::new(self)
    }
    
    fn generate_embedding(&self, content: &str) -> Result<Vec<f32>, Status> {
        let documents = vec![content.to_string()];
        // FIX: Added 'mut' here because fastembed v5 requires mutable access
        let mut embedder = self.embedder.lock()
            .map_err(|_| Status::internal("AI Engine lock failure"))?;
        
        let embeddings = embedder.embed(documents, None)
            .map_err(|e| Status::internal(format!("Embedding failed: {}", e)))?;
        
        embeddings.into_iter().next()
            .ok_or_else(|| Status::internal("No embedding generated"))
    }
}

#[tonic::async_trait]
impl MemoryService for MemoryServiceImpl {
    async fn store_memory(&self, req: Request<StoreMemoryRequest>) -> Result<Response<StoreMemoryResponse>, Status> {
        let r = req.into_inner();
        if r.content.trim().is_empty() { return Err(Status::invalid_argument("Content required")); }
        
        let id = Uuid::new_v4().to_string();
        let now = chrono::Utc::now().timestamp();
        
        let embedding = self.generate_embedding(&r.content)?;
        
        self.db.store_memory(&id, &r.content, &embedding, &r.metadata, &r.tags, now, now)
            .await
            .map_err(|e| Status::internal(format!("DB Error: {}", e)))?;
        
        tracing::info!("Indexed memory {}", id);
        Ok(Response::new(StoreMemoryResponse { memory_id: id, success: true, message: "Saved to Cloud".into() }))
    }
    
    async fn search_memories(&self, req: Request<SearchMemoriesRequest>) -> Result<Response<SearchMemoriesResponse>, Status> {
        let r = req.into_inner();
        
        let matches = self.db.search_memories(&r.query_embedding, r.limit, r.similarity_threshold)
            .await
            .map_err(|e| Status::internal(format!("Search failed: {}", e)))?;
        
        let proto_matches = matches.into_iter().map(|m| MemoryMatch {
            memory: Some(Memory {
                id: m.id,
                content: m.content,
                metadata: m.metadata,
                embedding: vec![],
                created_at: Some(prost_types::Timestamp { seconds: m.created_at, nanos: 0 }),
                updated_at: Some(prost_types::Timestamp { seconds: m.updated_at, nanos: 0 }),
                tags: m.tags,
            }),
            similarity_score: 0.99,
        }).collect();
        
        Ok(Response::new(SearchMemoriesResponse { matches: proto_matches }))
    }

    async fn query_memories(&self, req: Request<QueryMemoriesRequest>) -> Result<Response<QueryMemoriesResponse>, Status> {
        let r = req.into_inner();
        let limit = if r.limit > 0 { r.limit } else { 50 };
        
        let results = self.db.query_memories(&r.query, limit)
            .await
            .map_err(|e| Status::internal(e.to_string()))?;
            
        let memories: Vec<Memory> = results.into_iter().map(|m| Memory {
            id: m.id, content: m.content, metadata: m.metadata, embedding: vec![],
            created_at: Some(prost_types::Timestamp { seconds: m.created_at, nanos: 0 }),
            updated_at: Some(prost_types::Timestamp { seconds: m.updated_at, nanos: 0 }),
            tags: m.tags,
        }).collect();
        
        Ok(Response::new(QueryMemoriesResponse { total_count: memories.len() as i32, memories }))
    }
    
    async fn get_memory(&self, req: Request<GetMemoryRequest>) -> Result<Response<GetMemoryResponse>, Status> {
        let r = req.into_inner();
        let result = self.db.get_memory(&r.memory_id)
            .await
            .map_err(|e| Status::internal(e.to_string()))?;
        
        match result {
            Some(m) => Ok(Response::new(GetMemoryResponse { memory: Some(Memory {
                id: m.id, content: m.content, metadata: m.metadata, embedding: vec![],
                created_at: Some(prost_types::Timestamp { seconds: m.created_at, nanos: 0 }),
                updated_at: Some(prost_types::Timestamp { seconds: m.updated_at, nanos: 0 }),
                tags: m.tags,
            })})),
            None => Err(Status::not_found("Not found")),
        }
    }

    async fn delete_memory(&self, req: Request<DeleteMemoryRequest>) -> Result<Response<DeleteMemoryResponse>, Status> {
        let r = req.into_inner();
        let success = self.db.delete_memory(&r.memory_id)
            .await
            .map_err(|e| Status::internal(e.to_string()))?;
            
        Ok(Response::new(DeleteMemoryResponse { success, message: if success { "Deleted".into() } else { "Not found".into() } }))
    }

    async fn get_recent_memories(&self, req: Request<GetRecentMemoriesRequest>) -> Result<Response<GetRecentMemoriesResponse>, Status> {
        let r = req.into_inner();
        
        let results = self.db.get_recent_memories(r.limit)
            .await
            .map_err(|e| Status::internal(format!("Database error: {}", e)))?;

        let memories: Vec<Memory> = results.into_iter().map(|m| Memory {
            id: m.id,
            content: m.content,
            metadata: m.metadata,
            embedding: vec![], 
            created_at: Some(prost_types::Timestamp { seconds: m.created_at, nanos: 0 }),
            updated_at: Some(prost_types::Timestamp { seconds: m.updated_at, nanos: 0 }),
            tags: m.tags,
        }).collect();
        
        Ok(Response::new(GetRecentMemoriesResponse { memories }))
    }
}