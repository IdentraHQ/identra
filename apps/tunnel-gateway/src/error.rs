use thiserror::Error;

#[derive(Error, Debug)]
pub enum GatewayError {
    #[error("gRPC error: {0}")]
    Grpc(#[from] tonic::Status),
    
    #[error("Configuration error: {0}")]
    Config(String),
    
    #[error("Service error: {0}")]
    Service(String),
    
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    
    #[error("Transport error: {0}")]
    Transport(#[from] tonic::transport::Error),
}

pub type Result<T> = std::result::Result<T, GatewayError>;
