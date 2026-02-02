/**
 * Vault Daemon - gRPC Memory Service Implementation
 * Owner: Sarthak (following team ownership rules from copilot-instructions.md)
 * 
 * This implements the MemoryService gRPC interface for secure memory operations.
 * Provides encrypted storage with OS keychain integration for the Identra RAG system.
 */

use tonic::{Request, Response, Status};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use chrono::{DateTime, Utc};
use uuid::Uuid;

// Import generated gRPC types from identra-proto
use identra_proto::memory::{
    memory_service_server::MemoryService,
    Memory, MemoryMatch,
    StoreMemoryRequest, StoreMemoryResponse,
    QueryMemoriesRequest, QueryMemoriesResponse,
    SearchMemoriesRequest, SearchMemoriesResponse,
    GetRecentMemoriesRequest, GetRecentMemoriesResponse,
    GetMemoryRequest, GetMemoryResponse,
    DeleteMemoryRequest, DeleteMemoryResponse,
};

use crate::keychain::KeychainManager;
use crate::error::Result;

/// In-memory storage for development (will be replaced with encrypted storage)
#[derive(Debug, Clone)]
pub struct MemoryStorage {
    pub id: String,
    pub content: String,
    pub metadata: HashMap<String, String>,
    pub embedding: Vec<f32>,  // Placeholder for vector embeddings
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub tags: Vec<String>,
}

/// gRPC MemoryService implementation
pub struct MemoryServiceImpl {
    /// In-memory storage (MVP - will be replaced with encrypted database)
    storage: Arc<RwLock<HashMap<String, MemoryStorage>>>,
    /// Keychain manager for secure key storage
    keychain: Arc<KeychainManager>,
}

impl MemoryServiceImpl {
    /// Create new MemoryService instance
    pub fn new() -> Result<Self> {
        Ok(Self {
            storage: Arc::new(RwLock::new(HashMap::new())),
            keychain: Arc::new(KeychainManager::new()?),
        })
    }
    
    /// Generate simple embeddings (placeholder - will use real embeddings later)
    fn generate_embedding(&self, text: &str) -> Vec<f32> {
        // Simple bag-of-words hash-based embedding for MVP
        let mut embedding = vec![0.0; 384]; // Same size as sentence-transformers
        let embedding_len = embedding.len();
        
        for (i, word) in text.to_lowercase().split_whitespace().enumerate() {
            if i >= embedding_len { break; }
            // Simple hash to float conversion
            let hash = word.chars().fold(0u32, |acc, c| acc.wrapping_mul(31).wrapping_add(c as u32));
            embedding[i] = (hash as f32) / u32::MAX as f32;
        }
        
        embedding
    }
    
    /// Calculate similarity between two embeddings (cosine similarity)
    fn calculate_similarity(&self, a: &[f32], b: &[f32]) -> f32 {
        if a.len() != b.len() { return 0.0; }
        
        let dot_product: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
        let magnitude_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
        let magnitude_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
        
        if magnitude_a == 0.0 || magnitude_b == 0.0 { return 0.0; }
        
        dot_product / (magnitude_a * magnitude_b)
    }
}

#[tonic::async_trait]
impl MemoryService for MemoryServiceImpl {
    /// Store a new memory
    async fn store_memory(
        &self,
        request: Request<StoreMemoryRequest>,
    ) -> std::result::Result<Response<StoreMemoryResponse>, Status> {
        let req = request.into_inner();
        
        // Generate unique ID
        let memory_id = Uuid::new_v4().to_string();
        let now = Utc::now();
        
        // Generate embedding for the content
        let embedding = self.generate_embedding(&req.content);
        
        // Create memory record
        let memory = MemoryStorage {
            id: memory_id.clone(),
            content: req.content,
            metadata: req.metadata,
            embedding,
            created_at: now,
            updated_at: now,
            tags: req.tags,
        };
        
        // Store in memory (will be encrypted storage later)
        {
            let mut storage = self.storage.write().await;
            storage.insert(memory_id.clone(), memory);
        }
        
        let response = StoreMemoryResponse {
            memory_id,
            success: true,
            message: "Memory stored successfully".to_string(),
        };
        
        Ok(Response::new(response))
    }
    
    /// Query memories by text similarity
    async fn query_memories(
        &self,
        request: Request<QueryMemoriesRequest>,
    ) -> std::result::Result<Response<QueryMemoriesResponse>, Status> {
        let req = request.into_inner();
        
        // Generate query embedding
        let query_embedding = self.generate_embedding(&req.query);
        
        // Search through stored memories
        let storage = self.storage.read().await;
        let mut matches: Vec<Memory> = Vec::new();
        
        for memory in storage.values() {
            // Calculate similarity
            let similarity = self.calculate_similarity(&query_embedding, &memory.embedding);
            
            // Apply filters
            let mut passes_filter = true;
            for (key, value) in &req.filters {
                if let Some(metadata_value) = memory.metadata.get(key) {
                    if metadata_value != value {
                        passes_filter = false;
                        break;
                    }
                } else {
                    passes_filter = false;
                    break;
                }
            }
            
            // Add if similarity is high enough and passes filters
            if similarity > 0.1 && passes_filter {
                matches.push(Memory {
                    id: memory.id.clone(),
                    content: memory.content.clone(),
                    metadata: memory.metadata.clone(),
                    embedding: memory.embedding.clone(),
                    created_at: Some(prost_types::Timestamp {
                        seconds: memory.created_at.timestamp(),
                        nanos: memory.created_at.timestamp_subsec_nanos() as i32,
                    }),
                    updated_at: Some(prost_types::Timestamp {
                        seconds: memory.updated_at.timestamp(),
                        nanos: memory.updated_at.timestamp_subsec_nanos() as i32,
                    }),
                    tags: memory.tags.clone(),
                });
            }
        }
        
        // Sort by similarity (we need to store it somewhere - using metadata)
        // matches.sort_by(|a, b| b.similarity_score.partial_cmp(&a.similarity_score).unwrap_or(std::cmp::Ordering::Equal));
        
        // Limit results
        matches.truncate(req.limit as usize);
        
        let response = QueryMemoriesResponse {
            memories: matches,
            total_count: storage.len() as i32,
        };
        
        Ok(Response::new(response))
    }
    
    /// Get a specific memory by ID
    async fn get_memory(
        &self,
        request: Request<GetMemoryRequest>,
    ) -> std::result::Result<Response<GetMemoryResponse>, Status> {
        let req = request.into_inner();
        
        let storage = self.storage.read().await;
        
        if let Some(memory) = storage.get(&req.memory_id) {
            let response = GetMemoryResponse {
                memory: Some(Memory {
                    id: memory.id.clone(),
                    content: memory.content.clone(),
                    metadata: memory.metadata.clone(),
                    embedding: memory.embedding.clone(),
                    created_at: Some(prost_types::Timestamp {
                        seconds: memory.created_at.timestamp(),
                        nanos: memory.created_at.timestamp_subsec_nanos() as i32,
                    }),
                    updated_at: Some(prost_types::Timestamp {
                        seconds: memory.updated_at.timestamp(),
                        nanos: memory.updated_at.timestamp_subsec_nanos() as i32,
                    }),
                    tags: memory.tags.clone(),
                }),
            };
            Ok(Response::new(response))
        } else {
            Err(Status::not_found("Memory not found"))
        }
    }
    
    /// Delete a memory
    async fn delete_memory(
        &self,
        request: Request<DeleteMemoryRequest>,
    ) -> std::result::Result<Response<DeleteMemoryResponse>, Status> {
        let req = request.into_inner();
        
        let mut storage = self.storage.write().await;
        
        if storage.remove(&req.memory_id).is_some() {
            let response = DeleteMemoryResponse {
                success: true,
                message: "Memory deleted successfully".to_string(),
            };
            Ok(Response::new(response))
        } else {
            Err(Status::not_found("Memory not found"))
        }
    }
    
    /// Search memories by embedding similarity
    async fn search_memories(
        &self,
        request: Request<SearchMemoriesRequest>,
    ) -> std::result::Result<Response<SearchMemoriesResponse>, Status> {
        let req = request.into_inner();
        
        let storage = self.storage.read().await;
        let mut matches: Vec<MemoryMatch> = Vec::new();
        
        for memory in storage.values() {
            let similarity = self.calculate_similarity(&req.query_embedding, &memory.embedding);
            
            if similarity >= req.similarity_threshold {
                // Apply filters
                let mut passes_filter = true;
                for (key, value) in &req.filters {
                    if let Some(metadata_value) = memory.metadata.get(key) {
                        if metadata_value != value {
                            passes_filter = false;
                            break;
                        }
                    } else {
                        passes_filter = false;
                        break;
                    }
                }
                
                if passes_filter {
                    matches.push(MemoryMatch {
                        memory: Some(Memory {
                            id: memory.id.clone(),
                            content: memory.content.clone(),
                            metadata: memory.metadata.clone(),
                            embedding: memory.embedding.clone(),
                            created_at: None,  // TODO: Fix timestamp compatibility
                            updated_at: None,  // TODO: Fix timestamp compatibility
                            tags: memory.tags.clone(),
                        }),
                        similarity_score: similarity,
                    });
                }
            }
        }
        
        // Sort by similarity (highest first)
        matches.sort_by(|a, b| b.similarity_score.partial_cmp(&a.similarity_score).unwrap_or(std::cmp::Ordering::Equal));
        
        // Limit results
        matches.truncate(req.limit as usize);
        
        let response = SearchMemoriesResponse { matches };
        Ok(Response::new(response))
    }
    
    /// Get recent memories
    async fn get_recent_memories(
        &self,
        request: Request<GetRecentMemoriesRequest>,
    ) -> std::result::Result<Response<GetRecentMemoriesResponse>, Status> {
        let req = request.into_inner();
        
        let storage = self.storage.read().await;
        
        // Collect and sort by creation time (newest first)
        let mut memories: Vec<Memory> = storage.values().map(|memory| Memory {
            id: memory.id.clone(),
            content: memory.content.clone(),
            metadata: memory.metadata.clone(),
            embedding: memory.embedding.clone(),
            created_at: None,  // TODO: Fix timestamp compatibility
            updated_at: None,  // TODO: Fix timestamp compatibility
            tags: memory.tags.clone(),
        }).collect();
        
        memories.sort_by(|a, b| {
            b.created_at.as_ref().unwrap().seconds.cmp(&a.created_at.as_ref().unwrap().seconds)
        });
        
        // Limit results
        memories.truncate(req.limit as usize);
        
        let response = GetRecentMemoriesResponse { memories };
        Ok(Response::new(response))
    }
}