use identra_proto::auth::auth_service_server::AuthService;
use identra_proto::auth::{
    LoginRequest, LoginResponse, RefreshTokenRequest, RefreshTokenResponse, RegisterRequest,
    RegisterResponse, VerifyTokenRequest, VerifyTokenResponse,
};
use crate::auth::jwt::{hash_password, verify_password, JwtManager};
use crate::auth::user_db::UserDatabase;
use std::sync::Arc;
use tonic::{Request, Response, Status};

pub struct AuthServiceImpl {
    jwt_manager: Arc<JwtManager>,
    user_db: Arc<UserDatabase>,
}

impl AuthServiceImpl {
    pub fn new(jwt_manager: Arc<JwtManager>, user_db: Arc<UserDatabase>) -> Self {
        Self {
            jwt_manager,
            user_db,
        }
    }
}

#[tonic::async_trait]
impl AuthService for AuthServiceImpl {
    async fn register(
        &self,
        request: Request<RegisterRequest>,
    ) -> Result<Response<RegisterResponse>, Status> {
        let req = request.into_inner();
        
        // Validation
        if req.username.trim().is_empty() {
            return Ok(Response::new(RegisterResponse {
                success: false,
                message: "Username cannot be empty".to_string(),
                user_id: String::new(),
            }));
        }
        
        if req.password.len() < 8 {
            return Ok(Response::new(RegisterResponse {
                success: false,
                message: "Password must be at least 8 characters".to_string(),
                user_id: String::new(),
            }));
        }
        
        if req.email.trim().is_empty() || !req.email.contains('@') {
            return Ok(Response::new(RegisterResponse {
                success: false,
                message: "Invalid email address".to_string(),
                user_id: String::new(),
            }));
        }
        
        // Check if username already exists
        if self.user_db.username_exists(&req.username)
            .map_err(|e| Status::internal(format!("Database error: {}", e)))? {
            return Ok(Response::new(RegisterResponse {
                success: false,
                message: "Username already taken".to_string(),
                user_id: String::new(),
            }));
        }
        
        // Check if email already exists
        if self.user_db.email_exists(&req.email)
            .map_err(|e| Status::internal(format!("Database error: {}", e)))? {
            return Ok(Response::new(RegisterResponse {
                success: false,
                message: "Email already registered".to_string(),
                user_id: String::new(),
            }));
        }
        
        // Hash password
        let password_hash = hash_password(&req.password)
            .map_err(|e| Status::internal(format!("Password hashing error: {}", e)))?;
        
        // Create user
        let user_id = self.user_db.create_user(&req.username, &req.email, &password_hash)
            .map_err(|e| Status::internal(format!("Database error: {}", e)))?;
        
        tracing::info!("✅ User registered: {} ({})", req.username, user_id);
        
        Ok(Response::new(RegisterResponse {
            success: true,
            message: "User registered successfully".to_string(),
            user_id,
        }))
    }
    
    async fn login(
        &self,
        request: Request<LoginRequest>,
    ) -> Result<Response<LoginResponse>, Status> {
        let req = request.into_inner();
        
        // Get user from database
        let user = self.user_db.get_user_by_username(&req.username)
            .map_err(|e| Status::internal(format!("Database error: {}", e)))?;
        
        let user = match user {
            Some(u) => u,
            None => {
                return Ok(Response::new(LoginResponse {
                    success: false,
                    message: "Invalid username or password".to_string(),
                    access_token: String::new(),
                    refresh_token: String::new(),
                    expires_in: 0,
                }));
            }
        };
        
        // Verify password
        let valid = verify_password(&req.password, &user.password_hash)
            .map_err(|e| Status::internal(format!("Password verification error: {}", e)))?;
        
        if !valid {
            return Ok(Response::new(LoginResponse {
                success: false,
                message: "Invalid username or password".to_string(),
                access_token: String::new(),
                refresh_token: String::new(),
                expires_in: 0,
            }));
        }
        
        // Generate tokens
        let access_token = self.jwt_manager.generate_access_token(&user.user_id, &user.username)
            .map_err(|e| Status::internal(format!("Token generation error: {}", e)))?;
        
        let refresh_token = self.jwt_manager.generate_refresh_token(&user.user_id, &user.username)
            .map_err(|e| Status::internal(format!("Token generation error: {}", e)))?;
        
        // Update last login
        let _ = self.user_db.update_last_login(&user.user_id);
        
        tracing::info!("🔐 User logged in: {} ({})", user.username, user.user_id);
        
        Ok(Response::new(LoginResponse {
            success: true,
            message: "Login successful".to_string(),
            access_token,
            refresh_token,
            expires_in: 24 * 60 * 60, // 24 hours in seconds
        }))
    }
    
    async fn verify_token(
        &self,
        request: Request<VerifyTokenRequest>,
    ) -> Result<Response<VerifyTokenResponse>, Status> {
        let req = request.into_inner();
        
        match self.jwt_manager.validate_token(&req.token) {
            Ok(claims) => {
                Ok(Response::new(VerifyTokenResponse {
                    valid: true,
                    user_id: claims.sub,
                    username: claims.username,
                    expires_at: claims.exp,
                }))
            }
            Err(_) => {
                Ok(Response::new(VerifyTokenResponse {
                    valid: false,
                    user_id: String::new(),
                    username: String::new(),
                    expires_at: 0,
                }))
            }
        }
    }
    
    async fn refresh_token(
        &self,
        request: Request<RefreshTokenRequest>,
    ) -> Result<Response<RefreshTokenResponse>, Status> {
        let req = request.into_inner();
        
        // Validate refresh token
        let claims = match self.jwt_manager.validate_token(&req.refresh_token) {
            Ok(c) => c,
            Err(_) => {
                return Ok(Response::new(RefreshTokenResponse {
                    success: false,
                    access_token: String::new(),
                    expires_in: 0,
                }));
            }
        };
        
        // Check if it's actually a refresh token
        if claims.token_type != "refresh" {
            return Ok(Response::new(RefreshTokenResponse {
                success: false,
                access_token: String::new(),
                expires_in: 0,
            }));
        }
        
        // Generate new access token
        let access_token = self.jwt_manager.generate_access_token(&claims.sub, &claims.username)
            .map_err(|e| Status::internal(format!("Token generation error: {}", e)))?;
        
        tracing::info!("🔄 Token refreshed for user: {}", claims.username);
        
        Ok(Response::new(RefreshTokenResponse {
            success: true,
            access_token,
            expires_in: 24 * 60 * 60,
        }))
    }
}
