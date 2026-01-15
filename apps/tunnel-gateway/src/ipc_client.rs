use interprocess::local_socket::{
    tokio::{prelude::*, Stream},
    GenericNamespaced,
};
use serde::{Deserialize, Serialize};
use std::error::Error;
use std::fmt;
use tokio::io::{AsyncReadExt, AsyncWriteExt};

const IPC_PIPE_NAME: &str = "@identra-vault";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum VaultRequest {
    Store { identity_id: String, key: Vec<u8> },
    Retrieve { identity_id: String },
    Delete { identity_id: String },
    Exists { identity_id: String },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum VaultResponse {
    Success { message: String },
    KeyData { key: Vec<u8> },
    Exists { exists: bool },
    Error { message: String },
}

#[derive(Debug)]
pub enum VaultClientError {
    ConnectionFailed(String),
    SendFailed(String),
    ReceiveFailed(String),
    SerializationError(String),
}

impl fmt::Display for VaultClientError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::ConnectionFailed(msg) => write!(f, "Failed to connect to vault: {}", msg),
            Self::SendFailed(msg) => write!(f, "Failed to send request: {}", msg),
            Self::ReceiveFailed(msg) => write!(f, "Failed to receive response: {}", msg),
            Self::SerializationError(msg) => write!(f, "Serialization error: {}", msg),
        }
    }
}

impl Error for VaultClientError {}

pub struct VaultClient {
    stream: Stream,
}

impl VaultClient {
    pub async fn connect() -> Result<Self, VaultClientError> {
        let name = IPC_PIPE_NAME.to_ns_name::<GenericNamespaced>()
            .map_err(|e| VaultClientError::ConnectionFailed(e.to_string()))?;
        
        let stream = Stream::connect(name)
            .await
            .map_err(|e| VaultClientError::ConnectionFailed(e.to_string()))?;

        Ok(Self { stream })
    }

    pub async fn send_request(&mut self, request: VaultRequest) -> Result<VaultResponse, VaultClientError> {
        // Serialize request
        let request_data = serde_json::to_vec(&request)
            .map_err(|e| VaultClientError::SerializationError(e.to_string()))?;
        
        // Send length prefix (4 bytes)
        let len = (request_data.len() as u32).to_le_bytes();
        self.stream.write_all(&len)
            .await
            .map_err(|e| VaultClientError::SendFailed(e.to_string()))?;
        
        // Send request data
        self.stream.write_all(&request_data)
            .await
            .map_err(|e| VaultClientError::SendFailed(e.to_string()))?;
        
        self.stream.flush()
            .await
            .map_err(|e| VaultClientError::SendFailed(e.to_string()))?;

        // Read response length
        let mut len_buf = [0u8; 4];
        self.stream.read_exact(&mut len_buf)
            .await
            .map_err(|e| VaultClientError::ReceiveFailed(e.to_string()))?;
        let response_len = u32::from_le_bytes(len_buf) as usize;

        // Read response data
        let mut response_data = vec![0u8; response_len];
        self.stream.read_exact(&mut response_data)
            .await
            .map_err(|e| VaultClientError::ReceiveFailed(e.to_string()))?;

        // Deserialize response
        let response: VaultResponse = serde_json::from_slice(&response_data)
            .map_err(|e| VaultClientError::SerializationError(e.to_string()))?;

        Ok(response)
    }

    pub async fn store_key(&mut self, identity_id: String, key: Vec<u8>) -> Result<String, VaultClientError> {
        let response = self.send_request(VaultRequest::Store { identity_id, key }).await?;
        match response {
            VaultResponse::Success { message } => Ok(message),
            VaultResponse::Error { message } => Err(VaultClientError::ReceiveFailed(message)),
            _ => Err(VaultClientError::ReceiveFailed("Unexpected response type".to_string())),
        }
    }

    pub async fn retrieve_key(&mut self, identity_id: String) -> Result<Vec<u8>, VaultClientError> {
        let response = self.send_request(VaultRequest::Retrieve { identity_id }).await?;
        match response {
            VaultResponse::KeyData { key } => Ok(key),
            VaultResponse::Error { message } => Err(VaultClientError::ReceiveFailed(message)),
            _ => Err(VaultClientError::ReceiveFailed("Unexpected response type".to_string())),
        }
    }

    pub async fn delete_key(&mut self, identity_id: String) -> Result<String, VaultClientError> {
        let response = self.send_request(VaultRequest::Delete { identity_id }).await?;
        match response {
            VaultResponse::Success { message } => Ok(message),
            VaultResponse::Error { message } => Err(VaultClientError::ReceiveFailed(message)),
            _ => Err(VaultClientError::ReceiveFailed("Unexpected response type".to_string())),
        }
    }

    pub async fn key_exists(&mut self, identity_id: String) -> Result<bool, VaultClientError> {
        let response = self.send_request(VaultRequest::Exists { identity_id }).await?;
        match response {
            VaultResponse::Exists { exists } => Ok(exists),
            VaultResponse::Error { message } => Err(VaultClientError::ReceiveFailed(message)),
            _ => Err(VaultClientError::ReceiveFailed("Unexpected response type".to_string())),
        }
    }
}
