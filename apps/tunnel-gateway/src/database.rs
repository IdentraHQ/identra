use sqlx::postgres::{PgPoolOptions, PgPool};
use sqlx::Row; 
use uuid::Uuid;
use serde_json::Value;
use std::collections::HashMap;

// Shared model for Service <-> DB
use crate::services::memory::MemoryModel;

#[derive(Clone)]
pub struct MemoryDatabase {
    pool: PgPool,
}

impl MemoryDatabase {
    pub async fn connect(database_url: &str) -> Result<Self, sqlx::Error> {
        tracing::info!("🔌 Connecting to Supabase...");
        
        let pool = PgPoolOptions::new()
            .max_connections(10)
            .connect(database_url)
            .await?;

        tracing::info!("✅ Connected to Supabase Postgres.");
        
        Ok(Self { pool })
    }

    pub async fn store_memory(
        &self,
        id: &str,
        content: &str,
        embedding: &[f32],
        metadata: &HashMap<String, String>,
        tags: &[String],
        created_at: i64,
        updated_at: i64,
    ) -> Result<(), sqlx::Error> {
        let uuid = Uuid::parse_str(id).unwrap_or_default();
        let metadata_json = serde_json::to_value(metadata).unwrap();

        // Use pgvector syntax for insertion
        sqlx::query(
            r#"
            INSERT INTO memories (id, content, embedding, metadata, tags, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            "#
        )
        .bind(uuid)
        .bind(content)
        .bind(embedding) 
        .bind(metadata_json)
        .bind(tags)
        .bind(created_at)
        .bind(updated_at)
        .execute(&self.pool)
        .await?;

        Ok(())
    }

    pub async fn search_memories(
        &self,
        embedding: &[f32],
        limit: i32,
        threshold: f32,
    ) -> Result<Vec<MemoryModel>, sqlx::Error> {
        // Native Vector Search: 1 - (embedding <=> query)
        let rows = sqlx::query(
            r#"
            SELECT id, content, metadata, tags, created_at, updated_at
            FROM memories
            WHERE 1 - (embedding <=> $1) > $2
            ORDER BY embedding <=> $1
            LIMIT $3
            "#
        )
        .bind(embedding)
        .bind(threshold)
        .bind(limit)
        .fetch_all(&self.pool)
        .await?;

        self.map_rows(rows)
    }

    // NEW: Fetch recent memories sorted by time
    pub async fn get_recent_memories(&self, limit: i32) -> Result<Vec<MemoryModel>, sqlx::Error> {
        let limit = if limit <= 0 { 50 } else { limit };
        
        let rows = sqlx::query(
            r#"
            SELECT id, content, metadata, tags, created_at, updated_at 
            FROM memories 
            ORDER BY created_at DESC 
            LIMIT $1
            "#
        )
        .bind(limit)
        .fetch_all(&self.pool)
        .await?;

        self.map_rows(rows)
    }

    pub async fn get_memory(&self, id: &str) -> Result<Option<MemoryModel>, sqlx::Error> {
        let uuid = Uuid::parse_str(id).unwrap_or_default();
        let row = sqlx::query("SELECT id, content, metadata, tags, created_at, updated_at FROM memories WHERE id = $1")
            .bind(uuid)
            .fetch_optional(&self.pool)
            .await?;
            
        match row {
            Some(row) => {
                let rows = vec![row];
                let mut results = self.map_rows(rows)?;
                Ok(results.pop())
            },
            None => Ok(None)
        }
    }

    pub async fn query_memories(&self, query: &str, limit: i32) -> Result<Vec<MemoryModel>, sqlx::Error> {
        let pattern = format!("%{}%", query);
        let rows = sqlx::query(
            "SELECT id, content, metadata, tags, created_at, updated_at FROM memories WHERE content ILIKE $1 LIMIT $2"
        )
        .bind(pattern)
        .bind(limit)
        .fetch_all(&self.pool)
        .await?;
        
        self.map_rows(rows)
    }

    pub async fn delete_memory(&self, id: &str) -> Result<bool, sqlx::Error> {
        let uuid = Uuid::parse_str(id).unwrap_or_default();
        let result = sqlx::query("DELETE FROM memories WHERE id = $1")
            .bind(uuid)
            .execute(&self.pool)
            .await?;
        Ok(result.rows_affected() > 0)
    }

    // Helper to map SQL rows to Rust structs
    fn map_rows(&self, rows: Vec<sqlx::postgres::PgRow>) -> Result<Vec<MemoryModel>, sqlx::Error> {
        let results = rows.into_iter().map(|row| {
            let id: Uuid = row.get("id");
            let meta_val: Value = row.get("metadata");
            let metadata: HashMap<String, String> = serde_json::from_value(meta_val).unwrap_or_default();

            MemoryModel {
                id: id.to_string(),
                content: row.get("content"),
                metadata,
                embedding: vec![], // Optimization: Don't return vector to client
                tags: row.get::<Option<Vec<String>>, _>("tags").unwrap_or_default(),
                created_at: row.get("created_at"),
                updated_at: row.get("updated_at"),
            }
        }).collect();
        Ok(results)
    }
}