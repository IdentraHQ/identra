use rusqlite::{Connection, Result as SqlResult, params};
use serde_json;
use std::collections::HashMap;
use std::path::Path;
use std::sync::{Arc, Mutex};

/// Database handler for persistent memory storage
pub struct MemoryDatabase {
    conn: Arc<Mutex<Connection>>,
}

impl MemoryDatabase {
    /// Initialize database with schema
    pub fn new<P: AsRef<Path>>(path: P) -> SqlResult<Self> {
        let conn = Connection::open(path)?;
        
        // Create schema
        conn.execute(
            "CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                embedding BLOB NOT NULL,
                metadata TEXT NOT NULL,
                tags TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )",
            [],
        )?;
        
        // Create index for faster queries
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_created_at ON memories(created_at DESC)",
            [],
        )?;
        
        tracing::info!("✅ Memory database initialized");
        
        Ok(Self {
            conn: Arc::new(Mutex::new(conn)),
        })
    }
    
    /// Store a memory in the database
    pub fn store_memory(
        &self,
        id: &str,
        content: &str,
        embedding: &[f32],
        metadata: &HashMap<String, String>,
        tags: &[String],
        created_at: i64,
        updated_at: i64,
    ) -> SqlResult<()> {
        let conn = self.conn.lock().unwrap();
        
        // Serialize embedding to bytes
        let embedding_bytes: Vec<u8> = embedding
            .iter()
            .flat_map(|f| f.to_le_bytes())
            .collect();
        
        // Serialize metadata and tags to JSON
        let metadata_json = serde_json::to_string(metadata).unwrap();
        let tags_json = serde_json::to_string(tags).unwrap();
        
        conn.execute(
            "INSERT OR REPLACE INTO memories 
             (id, content, embedding, metadata, tags, created_at, updated_at)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
            params![
                id,
                content,
                embedding_bytes,
                metadata_json,
                tags_json,
                created_at,
                updated_at
            ],
        )?;
        
        Ok(())
    }
    
    /// Retrieve a memory by ID
    pub fn get_memory(&self, id: &str) -> SqlResult<Option<StoredMemoryRow>> {
        let conn = self.conn.lock().unwrap();
        
        let mut stmt = conn.prepare(
            "SELECT id, content, embedding, metadata, tags, created_at, updated_at 
             FROM memories WHERE id = ?1"
        )?;
        
        let result = stmt.query_row(params![id], |row| {
            Ok(StoredMemoryRow {
                id: row.get(0)?,
                content: row.get(1)?,
                embedding_bytes: row.get(2)?,
                metadata_json: row.get(3)?,
                tags_json: row.get(4)?,
                created_at: row.get(5)?,
                updated_at: row.get(6)?,
            })
        });
        
        match result {
            Ok(row) => Ok(Some(row)),
            Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
            Err(e) => Err(e),
        }
    }
    
    /// Query memories by text search
    pub fn query_memories(&self, query: &str, limit: i32) -> SqlResult<Vec<StoredMemoryRow>> {
        let conn = self.conn.lock().unwrap();
        
        let query_pattern = format!("%{}%", query.to_lowercase());
        
        let mut stmt = conn.prepare(
            "SELECT id, content, embedding, metadata, tags, created_at, updated_at 
             FROM memories 
             WHERE LOWER(content) LIKE ?1 OR LOWER(tags) LIKE ?1
             ORDER BY created_at DESC
             LIMIT ?2"
        )?;
        
        let rows = stmt.query_map(params![query_pattern, limit], |row| {
            Ok(StoredMemoryRow {
                id: row.get(0)?,
                content: row.get(1)?,
                embedding_bytes: row.get(2)?,
                metadata_json: row.get(3)?,
                tags_json: row.get(4)?,
                created_at: row.get(5)?,
                updated_at: row.get(6)?,
            })
        })?;
        
        let mut memories = Vec::new();
        for row in rows {
            memories.push(row?);
        }
        
        Ok(memories)
    }
    
    /// Get all memories for vector search
    pub fn get_all_memories(&self) -> SqlResult<Vec<StoredMemoryRow>> {
        let conn = self.conn.lock().unwrap();
        
        let mut stmt = conn.prepare(
            "SELECT id, content, embedding, metadata, tags, created_at, updated_at 
             FROM memories"
        )?;
        
        let rows = stmt.query_map([], |row| {
            Ok(StoredMemoryRow {
                id: row.get(0)?,
                content: row.get(1)?,
                embedding_bytes: row.get(2)?,
                metadata_json: row.get(3)?,
                tags_json: row.get(4)?,
                created_at: row.get(5)?,
                updated_at: row.get(6)?,
            })
        })?;
        
        let mut memories = Vec::new();
        for row in rows {
            memories.push(row?);
        }
        
        Ok(memories)
    }
    
    /// Delete a memory by ID
    pub fn delete_memory(&self, id: &str) -> SqlResult<bool> {
        let conn = self.conn.lock().unwrap();
        
        let rows_affected = conn.execute(
            "DELETE FROM memories WHERE id = ?1",
            params![id],
        )?;
        
        Ok(rows_affected > 0)
    }
    
    /// Count total memories
    pub fn count_memories(&self) -> SqlResult<i64> {
        let conn = self.conn.lock().unwrap();
        conn.query_row("SELECT COUNT(*) FROM memories", [], |row| row.get(0))
    }
}

/// Row representation from database
#[derive(Debug, Clone)]
pub struct StoredMemoryRow {
    pub id: String,
    pub content: String,
    pub embedding_bytes: Vec<u8>,
    pub metadata_json: String,
    pub tags_json: String,
    pub created_at: i64,
    pub updated_at: i64,
}

impl StoredMemoryRow {
    /// Deserialize embedding from bytes
    pub fn get_embedding(&self) -> Vec<f32> {
        self.embedding_bytes
            .chunks(4)
            .map(|bytes| {
                let array: [u8; 4] = bytes.try_into().unwrap();
                f32::from_le_bytes(array)
            })
            .collect()
    }
    
    /// Deserialize metadata from JSON
    pub fn get_metadata(&self) -> HashMap<String, String> {
        serde_json::from_str(&self.metadata_json).unwrap_or_default()
    }
    
    /// Deserialize tags from JSON
    pub fn get_tags(&self) -> Vec<String> {
        serde_json::from_str(&self.tags_json).unwrap_or_default()
    }
}
