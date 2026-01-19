use crate::auth::jwt::UserCredentials;
use rusqlite::{Connection, Result as SqlResult, params};
use std::path::Path;
use std::sync::{Arc, Mutex};
use uuid::Uuid;

/// User database for authentication
pub struct UserDatabase {
    conn: Arc<Mutex<Connection>>,
}

impl UserDatabase {
    /// Initialize user database with schema
    pub fn new<P: AsRef<Path>>(path: P) -> SqlResult<Self> {
        let conn = Connection::open(path)?;
        
        // Create users table
        conn.execute(
            "CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                last_login INTEGER
            )",
            [],
        )?;
        
        // Create index for faster username lookups
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_username ON users(username)",
            [],
        )?;
        
        tracing::info!("✅ User database initialized");
        
        Ok(Self {
            conn: Arc::new(Mutex::new(conn)),
        })
    }
    
    /// Create a new user
    pub fn create_user(
        &self,
        username: &str,
        email: &str,
        password_hash: &str,
    ) -> SqlResult<String> {
        let conn = self.conn.lock().unwrap();
        let user_id = Uuid::new_v4().to_string();
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs() as i64;
        
        conn.execute(
            "INSERT INTO users (id, username, email, password_hash, created_at)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            params![user_id, username, email, password_hash, now],
        )?;
        
        Ok(user_id)
    }
    
    /// Get user by username
    pub fn get_user_by_username(&self, username: &str) -> SqlResult<Option<UserCredentials>> {
        let conn = self.conn.lock().unwrap();
        
        let mut stmt = conn.prepare(
            "SELECT id, username, email, password_hash FROM users WHERE username = ?1"
        )?;
        
        let result = stmt.query_row(params![username], |row| {
            Ok(UserCredentials {
                user_id: row.get(0)?,
                username: row.get(1)?,
                email: row.get(2)?,
                password_hash: row.get(3)?,
            })
        });
        
        match result {
            Ok(user) => Ok(Some(user)),
            Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
            Err(e) => Err(e),
        }
    }
    
    /// Get user by ID
    pub fn get_user_by_id(&self, user_id: &str) -> SqlResult<Option<UserCredentials>> {
        let conn = self.conn.lock().unwrap();
        
        let mut stmt = conn.prepare(
            "SELECT id, username, email, password_hash FROM users WHERE id = ?1"
        )?;
        
        let result = stmt.query_row(params![user_id], |row| {
            Ok(UserCredentials {
                user_id: row.get(0)?,
                username: row.get(1)?,
                email: row.get(2)?,
                password_hash: row.get(3)?,
            })
        });
        
        match result {
            Ok(user) => Ok(Some(user)),
            Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
            Err(e) => Err(e),
        }
    }
    
    /// Check if username exists
    pub fn username_exists(&self, username: &str) -> SqlResult<bool> {
        let conn = self.conn.lock().unwrap();
        let count: i32 = conn.query_row(
            "SELECT COUNT(*) FROM users WHERE username = ?1",
            params![username],
            |row| row.get(0),
        )?;
        Ok(count > 0)
    }
    
    /// Check if email exists
    pub fn email_exists(&self, email: &str) -> SqlResult<bool> {
        let conn = self.conn.lock().unwrap();
        let count: i32 = conn.query_row(
            "SELECT COUNT(*) FROM users WHERE email = ?1",
            params![email],
            |row| row.get(0),
        )?;
        Ok(count > 0)
    }
    
    /// Update last login timestamp
    pub fn update_last_login(&self, user_id: &str) -> SqlResult<()> {
        let conn = self.conn.lock().unwrap();
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs() as i64;
        
        conn.execute(
            "UPDATE users SET last_login = ?1 WHERE id = ?2",
            params![now, user_id],
        )?;
        
        Ok(())
    }
}
