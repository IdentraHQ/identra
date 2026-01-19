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
use std::collections::HashMap;
use std::sync::Arc;
use tonic::{Request, Response, Status};
use uuid::Uuid;

pub struct MemoryServiceImpl {
    db: Arc<MemoryDatabase>,
}

impl MemoryServiceImpl {
    pub fn new(db: Arc<MemoryDatabase>) -> Self {
        Self { db }
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
            .unwrap()
            .as_secs() as i64;
        
        // Generate embedding from content
        let embedding = Self::generate_embedding(&req.content);
        
        // Store in database
        self.db
            .store_memory(
                &memory_id,
                &req.content,
                &embedding,
                &req.metadata,
                &req.tags,
                now,
                now,
            )
            .map_err(|e| Status::internal(format!("Database error: {}", e)))?;
        
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
        
        let limit = if req.limit > 0 { req.limit } else { 50 };
        
        // Query database with text search
        let rows = self
            .db
            .query_memories(&req.query, limit)
            .map_err(|e| Status::internal(format!("Database error: {}", e)))?;
        
        let memories: Vec<Memory> = rows
            .iter()
            .map(|row| Memory {
                id: row.id.clone(),
                content: row.content.clone(),
                metadata: row.get_metadata(),
                embedding: row.get_embedding(),
                created_at: Some(prost_types::Timestamp {
                    seconds: row.created_at,
                    nanos: 0,
                }),
                updated_at: Some(prost_types::Timestamp {
                    seconds: row.updated_at,
                    nanos: 0,
                }),
                tags: row.get_tags(),
            })
            .collect();
        
        let total_count = memories.len() as i32;
        
        tracing::info!("Query '{}' returned {} memories", req.query, total_count);
        
        Ok(Response::new(QueryMemoriesResponse {
            memories,
            total_count,
        }))
    }
    
    async fn get_memory(
        &self,
        request: Request<GetMemoryRequest>,
    ) -> Result<Response<GetMemoryResponse>, Status> {
        let req = request.into_inner();
        
        let row = self
            .db
            .get_memory(&req.memory_id)
            .map_err(|e| Status::internal(format!("Database error: {}", e)))?;
        
        let memory = row.map(|r| Memory {
            id: r.id.clone(),
            content: r.content.clone(),
            metadata: r.get_metadata(),
            embedding: r.get_embedding(),
            created_at: Some(prost_types::Timestamp {
                seconds: r.created_at,
                nanos: 0,
            }),
            updated_at: Some(prost_types::Timestamp {
                seconds: r.updated_at,
                nanos: 0,
            }),
            tags: r.get_tags(),
        });
        
        if memory.is_none() {
            return Err(Status::not_found(format!("Memory '{}' not found", req.memory_id)));
        }
        
        Ok(Response::new(GetMemoryResponse {
            memory,
        }))
    }
    
    async fn delete_memory(
        &self,
        request: Request<DeleteMemoryRequest>,
    ) -> Result<Response<DeleteMemoryResponse>, Status> {
        let req = request.into_inner();
        
        let existed = self
            .db
            .delete_memory(&req.memory_id)
            .map_err(|e| Status::internal(format!("Database error: {}", e)))?;
        
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
        
        // Load all memories for vector search
        let rows = self
            .db
            .get_all_memories()
            .map_err(|e| Status::internal(format!("Database error: {}", e)))?;
        
        let mut matches: Vec<MemoryMatch> = Vec::new();
        
        // Calculate similarity for each memory
        for row in &rows {
            let embedding = row.get_embedding();
            let similarity = Self::cosine_similarity(&req.query_embedding, &embedding);
            
            // Filter by threshold
            if similarity >= req.similarity_threshold {
                matches.push(MemoryMatch {
                    memory: Some(Memory {
                        id: row.id.clone(),
                        content: row.content.clone(),
                        metadata: row.get_metadata(),
                        embedding,
                        created_at: Some(prost_types::Timestamp {
                            seconds: row.created_at,
                            nanos: 0,
                        }),
                        updated_at: Some(prost_types::Timestamp {
                            seconds: row.updated_at,
                            nanos: 0,
                        }),
                        tags: row.get_tags(),
                    }),
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
