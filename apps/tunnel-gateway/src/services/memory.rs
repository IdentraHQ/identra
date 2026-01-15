use identra_proto::memory::{
    memory_service_server::{MemoryService, MemoryServiceServer},
    Memory, MemoryMatch,
    StoreMemoryRequest, StoreMemoryResponse,
    QueryMemoriesRequest, QueryMemoriesResponse,
    GetMemoryRequest, GetMemoryResponse,
    DeleteMemoryRequest, DeleteMemoryResponse,
    SearchMemoriesRequest, SearchMemoriesResponse,
};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tonic::{Request, Response, Status};
use uuid::Uuid;

#[derive(Clone, Debug)]
struct StoredMemory {
    id: String,
    content: String,
    metadata: HashMap<String, String>,
    embedding: Vec<f32>,
    created_at: prost_types::Timestamp,
    updated_at: prost_types::Timestamp,
    tags: Vec<String>,
}

impl From<StoredMemory> for Memory {
    fn from(stored: StoredMemory) -> Self {
        Memory {
            id: stored.id,
            content: stored.content,
            metadata: stored.metadata,
            embedding: stored.embedding,
            created_at: Some(stored.created_at),
            updated_at: Some(stored.updated_at),
            tags: stored.tags,
        }
    }
}

pub struct MemoryServiceImpl {
    // In-memory store for MVP (can be replaced with vector DB later)
    memories: Arc<RwLock<HashMap<String, StoredMemory>>>,
}

impl MemoryServiceImpl {
    pub fn new() -> Self {
        Self {
            memories: Arc::new(RwLock::new(HashMap::new())),
        }
    }
    
    pub fn into_server(self) -> MemoryServiceServer<Self> {
        MemoryServiceServer::new(self)
    }
    
    /// Calculate cosine similarity between two vectors
    fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
        if a.len() != b.len() || a.is_empty() {
            return 0.0;
        }
        
        let dot_product: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
        let magnitude_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
        let magnitude_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
        
        if magnitude_a == 0.0 || magnitude_b == 0.0 {
            return 0.0;
        }
        
        dot_product / (magnitude_a * magnitude_b)
    }
    
    /// Generate a simple embedding (placeholder - should be replaced with actual embedding model)
    fn generate_embedding(content: &str) -> Vec<f32> {
        // Simple hash-based embedding for MVP (384 dimensions like sentence-transformers)
        // TODO: Replace with actual embedding model (OpenAI, Cohere, local BERT, etc.)
        let mut embedding = vec![0.0f32; 384];
        
        for (i, byte) in content.bytes().enumerate() {
            let idx = (byte as usize + i) % 384;
            embedding[idx] += (byte as f32) / 255.0;
        }
        
        // Normalize
        let magnitude: f32 = embedding.iter().map(|x| x * x).sum::<f32>().sqrt();
        if magnitude > 0.0 {
            for val in &mut embedding {
                *val /= magnitude;
            }
        }
        
        embedding
    }
}

#[tonic::async_trait]
impl MemoryService for MemoryServiceImpl {
    async fn store_memory(
        &self,
        request: Request<StoreMemoryRequest>,
    ) -> Result<Response<StoreMemoryResponse>, Status> {
        let req = request.into_inner();
        
        if req.content.trim().is_empty() {
            return Err(Status::invalid_argument("Content cannot be empty"));
        }
        
        let memory_id = Uuid::new_v4().to_string();
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap();
        let timestamp = prost_types::Timestamp {
            seconds: now.as_secs() as i64,
            nanos: now.subsec_nanos() as i32,
        };
        
        // Generate embedding from content
        let embedding = Self::generate_embedding(&req.content);
        
        let stored_memory = StoredMemory {
            id: memory_id.clone(),
            content: req.content.clone(),
            metadata: req.metadata,
            embedding,
            created_at: timestamp.clone(),
            updated_at: timestamp,
            tags: req.tags,
        };
        
        let mut memories = self.memories.write().await;
        memories.insert(memory_id.clone(), stored_memory);
        
        tracing::info!("Stored memory: {} (content length: {})", memory_id, req.content.len());
        
        Ok(Response::new(StoreMemoryResponse {
            memory_id,
            success: true,
            message: "Memory stored successfully".to_string(),
        }))
    }
    
    async fn query_memories(
        &self,
        request: Request<QueryMemoriesRequest>,
    ) -> Result<Response<QueryMemoriesResponse>, Status> {
        let req = request.into_inner();
        let memories = self.memories.read().await;
        
        // Filter memories based on query (simple text matching for MVP)
        let query_lower = req.query.to_lowercase();
        let mut matching_memories: Vec<Memory> = memories
            .values()
            .filter(|m| {
                m.content.to_lowercase().contains(&query_lower) ||
                m.tags.iter().any(|tag| tag.to_lowercase().contains(&query_lower))
            })
            .cloned()
            .map(Memory::from)
            .collect();
        
        // Apply limit
        let limit = if req.limit > 0 {
            req.limit as usize
        } else {
            50 // Default limit
        };
        matching_memories.truncate(limit);
        
        let total_count = matching_memories.len() as i32;
        
        tracing::info!("Query '{}' returned {} memories", req.query, total_count);
        
        Ok(Response::new(QueryMemoriesResponse {
            memories: matching_memories,
            total_count,
        }))
    }
    
    async fn get_memory(
        &self,
        request: Request<GetMemoryRequest>,
    ) -> Result<Response<GetMemoryResponse>, Status> {
        let req = request.into_inner();
        let memories = self.memories.read().await;
        
        let memory = memories
            .get(&req.memory_id)
            .cloned()
            .map(Memory::from)
            .ok_or_else(|| Status::not_found(format!("Memory '{}' not found", req.memory_id)))?;
        
        Ok(Response::new(GetMemoryResponse {
            memory: Some(memory),
        }))
    }
    
    async fn delete_memory(
        &self,
        request: Request<DeleteMemoryRequest>,
    ) -> Result<Response<DeleteMemoryResponse>, Status> {
        let req = request.into_inner();
        let mut memories = self.memories.write().await;
        
        let existed = memories.remove(&req.memory_id).is_some();
        
        if existed {
            tracing::info!("Deleted memory: {}", req.memory_id);
            Ok(Response::new(DeleteMemoryResponse {
                success: true,
                message: format!("Memory '{}' deleted successfully", req.memory_id),
            }))
        } else {
            Ok(Response::new(DeleteMemoryResponse {
                success: false,
                message: format!("Memory '{}' not found", req.memory_id),
            }))
        }
    }
    
    async fn search_memories(
        &self,
        request: Request<SearchMemoriesRequest>,
    ) -> Result<Response<SearchMemoriesResponse>, Status> {
        let req = request.into_inner();
        
        if req.query_embedding.is_empty() {
            return Err(Status::invalid_argument("Query embedding cannot be empty"));
        }
        
        let memories = self.memories.read().await;
        let mut matches: Vec<MemoryMatch> = Vec::new();
        
        // Calculate similarity for each memory
        for memory in memories.values() {
            let similarity = Self::cosine_similarity(&req.query_embedding, &memory.embedding);
            
            // Filter by threshold
            if similarity >= req.similarity_threshold {
                matches.push(MemoryMatch {
                    memory: Some(Memory::from(memory.clone())),
                    similarity_score: similarity,
                });
            }
        }
        
        // Sort by similarity (highest first)
        matches.sort_by(|a, b| b.similarity_score.partial_cmp(&a.similarity_score).unwrap());
        
        // Apply limit
        let limit = if req.limit > 0 {
            req.limit as usize
        } else {
            10 // Default limit
        };
        matches.truncate(limit);
        
        tracing::info!("Vector search returned {} matches", matches.len());
        
        Ok(Response::new(SearchMemoriesResponse { matches }))
    }
}

impl Default for MemoryServiceImpl {
    fn default() -> Self {
        Self::new()
    }
}
