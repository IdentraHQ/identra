use identra_proto::memory::{
    memory_service_client::MemoryServiceClient,
    StoreMemoryRequest, QueryMemoriesRequest,
};
use std::collections::HashMap;
use tonic::transport::Channel;

pub struct GrpcClient {
    memory_client: MemoryServiceClient<Channel>,
}

impl GrpcClient {
    pub async fn connect() -> Result<Self, Box<dyn std::error::Error>> {
        let channel = Channel::from_static("http://[::1]:50051")
            .connect()
            .await?;
        
        let memory_client = MemoryServiceClient::new(channel);
        
        Ok(Self { memory_client })
    }
    
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
}
