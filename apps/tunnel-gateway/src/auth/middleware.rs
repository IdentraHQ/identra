use crate::auth::jwt::JwtManager;
use std::sync::Arc;
use tonic::{Request, Status};

/// gRPC interceptor for JWT authentication
#[derive(Clone)]
pub struct AuthInterceptor {
    jwt_manager: Arc<JwtManager>,
}

impl AuthInterceptor {
    pub fn new(jwt_manager: Arc<JwtManager>) -> Self {
        Self { jwt_manager }
    }
    
    /// Intercept and validate JWT token from metadata
    pub fn intercept<T>(&self, mut req: Request<T>) -> Result<Request<T>, Status> {
        // Get authorization header
        let token = match req.metadata().get("authorization") {
            Some(t) => t.to_str().map_err(|_| {
                Status::unauthenticated("Invalid authorization header")
            })?,
            None => {
                return Err(Status::unauthenticated("Missing authorization token"));
            }
        };
        
        // Extract token from "Bearer <token>" format
        let token = JwtManager::extract_token_from_header(token)
            .ok_or_else(|| Status::unauthenticated("Invalid token format. Use: Bearer <token>"))?;
        
        // Validate token
        let claims = self.jwt_manager.validate_token(&token)
            .map_err(|e| {
                tracing::warn!("Token validation failed: {}", e);
                Status::unauthenticated("Invalid or expired token")
            })?;
        
        // Add user info to request extensions for downstream services
        req.extensions_mut().insert(claims);
        
        Ok(req)
    }
}

/// Helper function to extract user ID from request extensions
pub fn get_user_id_from_request<T>(req: &Request<T>) -> Result<String, Status> {
    req.extensions()
        .get::<crate::auth::Claims>()
        .map(|claims| claims.sub.clone())
        .ok_or_else(|| Status::unauthenticated("User not authenticated"))
}

/// Helper function to extract username from request extensions
pub fn get_username_from_request<T>(req: &Request<T>) -> Result<String, Status> {
    req.extensions()
        .get::<crate::auth::Claims>()
        .map(|claims| claims.username.clone())
        .ok_or_else(|| Status::unauthenticated("User not authenticated"))
}
