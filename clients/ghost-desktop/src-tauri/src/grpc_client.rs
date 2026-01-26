use identra_proto::memory::{
    memory_service_client::MemoryServiceClient,
    StoreMemoryRequest, QueryMemoriesRequest, 
    SearchMemoriesRequest, GetRecentMemoriesRequest,
};
use identra_proto::auth::{
    auth_service_client::AuthServiceClient,
    LoginRequest, RegisterRequest,
};
use std::collections::HashMap;
use tonic::transport::Channel;

pub struct GrpcClient {
    memory_client: MemoryServiceClient<Channel>,
    auth_client: AuthServiceClient<Channel>,
}

impl GrpcClient {
    pub async fn connect() -> Result<Self, Box<dyn std::error::Error>> {
        // Connect to the Gateway
        let channel = Channel::from_static("http://[::1]:50051")
            .connect()
            .await?;
        
        Ok(Self { 
            memory_client: MemoryServiceClient::new(channel.clone()),
            auth_client: AuthServiceClient::new(channel),
        })
    }
    
    // --- MEMORY METHODS ---

    pub async fn store_memory(
        &mut self,
        content: String,
        metadata: HashMap<String, String>,
        tags: Vec<String>,
    ) -> Result<String, Box<dyn std::error::Error>> {
        let request = tonic::Request::new(StoreMemoryRequest {
            content,
            metadata,
            tags,
        });
        
        let response = self.memory_client.store_memory(request).await?;
        let resp = response.into_inner();
        
        if resp.success {
            Ok(resp.memory_id)
        } else {
            Err(format!("Storage failed: {}", resp.message).into())
        }
    }
    
    pub async fn query_memories(
        &mut self,
        query: String,
        limit: i32,
    ) -> Result<Vec<(String, String, i64)>, Box<dyn std::error::Error>> {
        let request = tonic::Request::new(QueryMemoriesRequest {
            query,
            limit,
            filters: HashMap::new(),
        });
        
        let response = self.memory_client.query_memories(request).await?;
        let memories = response.into_inner().memories;
        
        let result = memories.into_iter()
            .map(|m| {
                let created_at = m.created_at.map(|t| t.seconds).unwrap_or(0);
                (m.id, m.content, created_at)
            })
            .collect();
        
        Ok(result)
    }

    pub async fn search_memories(
        &mut self,
        query_embedding: Vec<f32>,
        limit: i32,
        similarity_threshold: f32,
    ) -> Result<Vec<(String, String, f32)>, Box<dyn std::error::Error>> {
        let request = tonic::Request::new(SearchMemoriesRequest {
            query_embedding,
            limit,
            similarity_threshold,
            filters: std::collections::HashMap::new(),
        });

        let response = self.memory_client.search_memories(request).await?;
        let matches = response.into_inner().matches;

        let result = matches.into_iter()
            .map(|m| {
                let mem = m.memory.unwrap_or_default();
                (mem.id, mem.content, m.similarity_score)
            })
            .collect();

        Ok(result)
    }

    pub async fn get_recent_memories(
        &mut self, 
        limit: i32
    ) -> Result<Vec<(String, String, i64)>, Box<dyn std::error::Error>> {
        let request = tonic::Request::new(GetRecentMemoriesRequest {
            limit,
        });

        let response = self.memory_client.get_recent_memories(request).await?;
        let memories = response.into_inner().memories;

        let result = memories.into_iter()
            .map(|m| {
                let created_at = m.created_at.map(|t| t.seconds).unwrap_or(0);
                (m.id, m.content, created_at)
            })
            .collect();

        Ok(result)
    }

    // --- AUTH METHODS ---

    pub async fn login(&mut self, username: String, password: String) -> Result<String, Box<dyn std::error::Error>> {
        let request = tonic::Request::new(LoginRequest {
            username,
            password,
        });

        let response = self.auth_client.login(request).await?;
        let resp = response.into_inner();

        if resp.success {
            Ok(resp.access_token)
        } else {
            Err(format!("Login failed: {}", resp.message).into())
        }
    }

    pub async fn register(&mut self, username: String, email: String, password: String) -> Result<String, Box<dyn std::error::Error>> {
        let request = tonic::Request::new(RegisterRequest {
            username,
            email,
            password,
        });

        let response = self.auth_client.register(request).await?;
        let resp = response.into_inner();

        if resp.success {
            Ok(resp.user_id)
        } else {
            Err(format!("Registration failed: {}", resp.message).into())
        }
    }
}