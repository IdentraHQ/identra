use identra_proto::memory::{
    memory_service_server::{MemoryService, MemoryServiceServer},
    Memory, MemoryMatch,
    StoreMemoryRequest, StoreMemoryResponse,
    QueryMemoriesRequest, QueryMemoriesResponse,
    GetMemoryRequest, GetMemoryResponse,
    DeleteMemoryRequest, DeleteMemoryResponse,
    SearchMemoriesRequest, SearchMemoriesResponse,
};
use crate::database::MemoryDatabase;
use std::sync::{Arc, Mutex};
use tonic::{Request, Response, Status};
use uuid::Uuid;
use fastembed::{TextEmbedding, InitOptions, EmbeddingModel};

pub struct MemoryServiceImpl {
    db: Arc<MemoryDatabase>,
    embedder: Arc<Mutex<TextEmbedding>>, 
}

impl MemoryServiceImpl {
    pub fn new(db: Arc<MemoryDatabase>) -> Self {
        tracing::info!("Initializing Neural Engine (all-MiniLM-L6-v2)...");
        let start = std::time::Instant::now();
        
        // Use Default trait and correct Enum capitalization
        let mut options = InitOptions::default();
        options.model_name = EmbeddingModel::AllMiniLML6V2;
        options.show_download_progress = true;

        let embedder = TextEmbedding::try_new(options)
            .expect("Failed to load local AI model");

        tracing::info!("AI Model loaded in {:.2?}", start.elapsed());

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
        
        // MutexGuard must be mutable to call .embed()
        let mut embedder = self.embedder.lock()
            .map_err(|_| Status::internal("Neural Engine lock poisoned"))?;
        
        let embeddings = embedder.embed(documents, None)
            .map_err(|e| Status::internal(format!("Embedding failed: {}", e)))?;
        
        embeddings.into_iter().next()
            .ok_or_else(|| Status::internal("No embedding produced"))
    }

    fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
        if a.len() != b.len() || a.is_empty() { return 0.0; }
        
        let dot = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum::<f32>();
        let mag_a = a.iter().map(|x| x * x).sum::<f32>().sqrt();
        let mag_b = b.iter().map(|x| x * x).sum::<f32>().sqrt();
        
        if mag_a <= f32::EPSILON || mag_b <= f32::EPSILON { return 0.0; }
        
        dot / (mag_a * mag_b)
    }
}

#[tonic::async_trait]
impl MemoryService for MemoryServiceImpl {
    async fn store_memory(&self, req: Request<StoreMemoryRequest>) -> Result<Response<StoreMemoryResponse>, Status> {
        let r = req.into_inner();
        if r.content.trim().is_empty() { return Err(Status::invalid_argument("Empty content")); }
        
        let id = Uuid::new_v4().to_string();
        let now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs() as i64;
        
        let embedding = self.generate_embedding(&r.content)?;
        
        self.db.store_memory(&id, &r.content, &embedding, &r.metadata, &r.tags, now, now)
            .map_err(|e| Status::internal(format!("DB Error: {}", e)))?;
        
        tracing::info!(id = %id, "Memory indexed");
        Ok(Response::new(StoreMemoryResponse { memory_id: id, success: true, message: "Indexed".into() }))
    }
    
    async fn search_memories(&self, req: Request<SearchMemoriesRequest>) -> Result<Response<SearchMemoriesResponse>, Status> {
        let r = req.into_inner();
        if r.query_embedding.is_empty() { return Err(Status::invalid_argument("Empty vector")); }
        
        let rows = self.db.get_all_memories()
            .map_err(|e| Status::internal(format!("DB Error: {}", e)))?;
        
        // FIX 4: Explicit type annotation and .clone() to avoid partial moves
        let mut matches: Vec<MemoryMatch> = rows.iter().filter_map(|row| {
            let emb = row.get_embedding();
            let score = Self::cosine_similarity(&r.query_embedding, &emb);
            
            if score >= r.similarity_threshold {
                Some(MemoryMatch {
                    memory: Some(Memory {
                        id: row.id.clone(),
                        content: row.content.clone(), // Clone needed here
                        metadata: row.get_metadata(),
                        embedding: emb,
                        created_at: Some(prost_types::Timestamp { seconds: row.created_at, nanos: 0 }),
                        updated_at: Some(prost_types::Timestamp { seconds: row.updated_at, nanos: 0 }),
                        tags: row.get_tags(),
                    }),
                    similarity_score: score,
                })
            } else { None }
        }).collect();
        
        matches.sort_by(|a, b| b.similarity_score.partial_cmp(&a.similarity_score).unwrap_or(std::cmp::Ordering::Equal));
        
        let limit = if r.limit > 0 { r.limit as usize } else { 10 };
        if matches.len() > limit { matches.truncate(limit); }
        
        Ok(Response::new(SearchMemoriesResponse { matches }))
    }

    async fn query_memories(&self, req: Request<QueryMemoriesRequest>) -> Result<Response<QueryMemoriesResponse>, Status> {
        let r = req.into_inner();
        let limit = if r.limit > 0 { r.limit } else { 50 };
        
        let rows = self.db.query_memories(&r.query, limit).map_err(|e| Status::internal(e.to_string()))?;
        
        // FIX 4: Explicit type and Clones
        let memories: Vec<Memory> = rows.iter().map(|row| Memory {
            id: row.id.clone(),
            content: row.content.clone(),
            metadata: row.get_metadata(),
            embedding: row.get_embedding(),
            created_at: Some(prost_types::Timestamp { seconds: row.created_at, nanos: 0 }),
            updated_at: Some(prost_types::Timestamp { seconds: row.updated_at, nanos: 0 }),
            tags: row.get_tags(),
        }).collect();
        
        Ok(Response::new(QueryMemoriesResponse { total_count: memories.len() as i32, memories }))
    }
    
    async fn get_memory(&self, req: Request<GetMemoryRequest>) -> Result<Response<GetMemoryResponse>, Status> {
        let r = req.into_inner();
        let row = self.db.get_memory(&r.memory_id).map_err(|e| Status::internal(e.to_string()))?;
        
        match row {
            Some(row) => Ok(Response::new(GetMemoryResponse { 
                memory: Some(Memory {
                    id: row.id.clone(),           
                    content: row.content.clone(), 
                    metadata: row.get_metadata(), // This works because row is still valid
                    embedding: row.get_embedding(),
                    created_at: Some(prost_types::Timestamp { seconds: row.created_at, nanos: 0 }),
                    updated_at: Some(prost_types::Timestamp { seconds: row.updated_at, nanos: 0 }),
                    tags: row.get_tags(),
                })
            })),
            None => Err(Status::not_found("Memory not found")),
        }
    }
    
    async fn delete_memory(&self, req: Request<DeleteMemoryRequest>) -> Result<Response<DeleteMemoryResponse>, Status> {
        let r = req.into_inner();
        let existed = self.db.delete_memory(&r.memory_id).map_err(|e| Status::internal(e.to_string()))?;
        Ok(Response::new(DeleteMemoryResponse { success: existed, message: if existed { "Deleted".into() } else { "Not found".into() } }))
    }
}