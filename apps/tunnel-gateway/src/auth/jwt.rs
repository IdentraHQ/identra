use chrono::{Duration, Utc};
use jsonwebtoken::{decode, encode, DecodingKey, EncodingKey, Header, Validation};
use serde::{Deserialize, Serialize};
use std::env;

const DEFAULT_JWT_SECRET: &str = "identra-dev-secret-change-in-production";
const ACCESS_TOKEN_EXPIRY_HOURS: i64 = 24;
const REFRESH_TOKEN_EXPIRY_DAYS: i64 = 30;

/// JWT Claims structure
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Claims {
    pub sub: String,        // Subject (user ID)
    pub username: String,   // Username
    pub exp: i64,          // Expiration time (Unix timestamp)
    pub iat: i64,          // Issued at (Unix timestamp)
    pub token_type: String, // "access" or "refresh"
}

/// User credentials for authentication
#[derive(Debug, Clone)]
pub struct UserCredentials {
    pub user_id: String,
    pub username: String,
    pub email: String,
    pub password_hash: String,
}

/// JWT token manager
pub struct JwtManager {
    encoding_key: EncodingKey,
    decoding_key: DecodingKey,
}

impl JwtManager {
    pub fn new() -> Self {
        let secret = env::var("JWT_SECRET").unwrap_or_else(|_| DEFAULT_JWT_SECRET.to_string());
        
        if secret == DEFAULT_JWT_SECRET {
            tracing::warn!("⚠️  Using default JWT secret! Set JWT_SECRET environment variable for production");
        }
        
        Self {
            encoding_key: EncodingKey::from_secret(secret.as_bytes()),
            decoding_key: DecodingKey::from_secret(secret.as_bytes()),
        }
    }
    
    /// Generate an access token (short-lived, 24 hours)
    pub fn generate_access_token(&self, user_id: &str, username: &str) -> Result<String, jsonwebtoken::errors::Error> {
        let now = Utc::now();
        let expiration = now + Duration::hours(ACCESS_TOKEN_EXPIRY_HOURS);
        
        let claims = Claims {
            sub: user_id.to_string(),
            username: username.to_string(),
            exp: expiration.timestamp(),
            iat: now.timestamp(),
            token_type: "access".to_string(),
        };
        
        encode(&Header::default(), &claims, &self.encoding_key)
    }
    
    /// Generate a refresh token (long-lived, 30 days)
    pub fn generate_refresh_token(&self, user_id: &str, username: &str) -> Result<String, jsonwebtoken::errors::Error> {
        let now = Utc::now();
        let expiration = now + Duration::days(REFRESH_TOKEN_EXPIRY_DAYS);
        
        let claims = Claims {
            sub: user_id.to_string(),
            username: username.to_string(),
            exp: expiration.timestamp(),
            iat: now.timestamp(),
            token_type: "refresh".to_string(),
        };
        
        encode(&Header::default(), &claims, &self.encoding_key)
    }
    
    /// Validate and decode a JWT token
    pub fn validate_token(&self, token: &str) -> Result<Claims, jsonwebtoken::errors::Error> {
        let token_data = decode::<Claims>(
            token,
            &self.decoding_key,
            &Validation::default(),
        )?;
        
        Ok(token_data.claims)
    }
    
    /// Extract token from Authorization header (format: "Bearer <token>")
    pub fn extract_token_from_header(auth_header: &str) -> Option<String> {
        if auth_header.starts_with("Bearer ") {
            Some(auth_header[7..].to_string())
        } else {
            None
        }
    }
}

impl Default for JwtManager {
    fn default() -> Self {
        Self::new()
    }
}

/// Hash a password using bcrypt
pub fn hash_password(password: &str) -> Result<String, bcrypt::BcryptError> {
    bcrypt::hash(password, bcrypt::DEFAULT_COST)
}

/// Verify a password against a hash
pub fn verify_password(password: &str, hash: &str) -> Result<bool, bcrypt::BcryptError> {
    bcrypt::verify(password, hash)
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_generate_and_validate_token() {
        let manager = JwtManager::new();
        let token = manager.generate_access_token("user123", "testuser").unwrap();
        let claims = manager.validate_token(&token).unwrap();
        
        assert_eq!(claims.sub, "user123");
        assert_eq!(claims.username, "testuser");
        assert_eq!(claims.token_type, "access");
    }
    
    #[test]
    fn test_password_hashing() {
        let password = "SecurePassword123!";
        let hash = hash_password(password).unwrap();
        
        assert!(verify_password(password, &hash).unwrap());
        assert!(!verify_password("WrongPassword", &hash).unwrap());
    }
    
    #[test]
    fn test_extract_token_from_header() {
        let token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9";
        let header = format!("Bearer {}", token);
        
        let extracted = JwtManager::extract_token_from_header(&header).unwrap();
        assert_eq!(extracted, token);
    }
}
