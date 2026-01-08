use identra_proto::health::{
    health_server::{Health, HealthServer},
    HealthCheckRequest, HealthCheckResponse,
    health_check_response::ServingStatus,
};
use std::sync::Arc;
use std::time::Instant;
use tokio::sync::RwLock;
use tonic::{Request, Response, Status};

pub struct HealthService {
    start_time: Instant,
    status: Arc<RwLock<ServingStatus>>,
}

impl HealthService {
    pub fn new() -> Self {
        Self {
            start_time: Instant::now(),
            status: Arc::new(RwLock::new(ServingStatus::Serving)),
        }
    }
    
    pub fn into_server(self) -> HealthServer<Self> {
        HealthServer::new(self)
    }
}

#[tonic::async_trait]
impl Health for HealthService {
    type WatchStream = tokio_stream::wrappers::ReceiverStream<Result<HealthCheckResponse, Status>>;
    
    async fn check(
        &self,
        _request: Request<HealthCheckRequest>,
    ) -> Result<Response<HealthCheckResponse>, Status> {
        let status = *self.status.read().await;
        let uptime = self.start_time.elapsed().as_secs() as i64;
        
        let response = HealthCheckResponse {
            status: status as i32,
            message: match status {
                ServingStatus::Serving => "Gateway is healthy".to_string(),
                ServingStatus::NotServing => "Gateway is not serving".to_string(),
                _ => "Unknown status".to_string(),
            },
            uptime_seconds: uptime,
        };
        
        Ok(Response::new(response))
    }
    
    async fn watch(
        &self,
        _request: Request<HealthCheckRequest>,
    ) -> Result<Response<Self::WatchStream>, Status> {
        // TODO: Implement streaming health updates
        Err(Status::unimplemented("Watch not yet implemented"))
    }
}

impl Default for HealthService {
    fn default() -> Self {
        Self::new()
    }
}
