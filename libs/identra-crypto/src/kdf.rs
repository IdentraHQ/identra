use crate::error::{CryptoError, Result};
use crate::KEY_SIZE;
use argon2::{
    password_hash::{PasswordHasher, SaltString},
    Argon2, Params, Version,
};
use zeroize::Zeroize;

/// Derived key wrapper
#[derive(Clone, Zeroize)]
#[zeroize(drop)]
pub struct DerivedKey([u8; KEY_SIZE]);

impl DerivedKey {
    /// Get key as bytes
    pub fn as_bytes(&self) -> &[u8] {
        &self.0
    }
    
    /// Convert to EncryptionKey
    pub fn to_encryption_key(&self) -> crate::EncryptionKey {
        crate::EncryptionKey::from_bytes(&self.0).expect("DerivedKey always has correct size")
    }
}

/// Key derivation parameters
#[derive(Clone)]
pub struct KeyDerivationParams {
    /// Memory cost in KiB (default: 64 MiB = 65536 KiB)
    pub memory_cost: u32,
    /// Time cost (iterations, default: 3)
    pub time_cost: u32,
    /// Parallelism (threads, default: 4)
    pub parallelism: u32,
}

impl Default for KeyDerivationParams {
    fn default() -> Self {
        Self {
            memory_cost: 65536, // 64 MiB
            time_cost: 3,
            parallelism: 4,
        }
    }
}

impl KeyDerivationParams {
    /// Create a fast preset for testing/development (less secure)
    pub fn fast() -> Self {
        Self {
            memory_cost: 8192,  // 8 MiB
            time_cost: 1,
            parallelism: 1,
        }
    }
    
    /// Create a secure preset for production
    pub fn secure() -> Self {
        Self::default()
    }
}

/// Derive an encryption key from a password using Argon2id
///
/// # Arguments
/// * `password` - Password/passphrase to derive key from
/// * `salt` - Unique salt (should be randomly generated and stored)
/// * `params` - Key derivation parameters (affects security and performance)
///
/// # Returns
/// Derived 32-byte key suitable for encryption
pub fn derive_key(
    password: &[u8],
    salt: &[u8],
    params: &KeyDerivationParams,
) -> Result<DerivedKey> {
    // Create Argon2id instance with custom parameters
    let argon2_params = Params::new(
        params.memory_cost,
        params.time_cost,
        params.parallelism,
        Some(KEY_SIZE),
    )
    .map_err(|e| CryptoError::KeyDerivation(e.to_string()))?;
    
    let argon2 = Argon2::new(
        argon2::Algorithm::Argon2id,
        Version::V0x13,
        argon2_params,
    );
    
    // Convert salt to SaltString format
    let salt_string = SaltString::encode_b64(salt)
        .map_err(|e| CryptoError::KeyDerivation(e.to_string()))?;
    
    // Derive key
    let password_hash = argon2
        .hash_password(password, &salt_string)
        .map_err(|e| CryptoError::KeyDerivation(e.to_string()))?;
    
    let hash_bytes = password_hash.hash
        .ok_or_else(|| CryptoError::KeyDerivation("No hash output".to_string()))?;
    
    let hash_slice = hash_bytes.as_bytes();
    
    if hash_slice.len() < KEY_SIZE {
        return Err(CryptoError::KeyDerivation(
            format!("Hash output too short: {} bytes", hash_slice.len())
        ));
    }
    
    let mut key = [0u8; KEY_SIZE];
    key.copy_from_slice(&hash_slice[..KEY_SIZE]);
    
    Ok(DerivedKey(key))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::generate_salt;
    
    #[test]
    fn test_derive_key() {
        let password = b"my_secure_password_123";
        let salt = generate_salt();
        let params = KeyDerivationParams::fast(); // Use fast params for tests
        
        let key = derive_key(password, &salt, &params).unwrap();
        assert_eq!(key.as_bytes().len(), KEY_SIZE);
    }
    
    #[test]
    fn test_same_password_same_salt_same_key() {
        let password = b"test_password";
        let salt = generate_salt();
        let params = KeyDerivationParams::fast();
        
        let key1 = derive_key(password, &salt, &params).unwrap();
        let key2 = derive_key(password, &salt, &params).unwrap();
        
        assert_eq!(key1.as_bytes(), key2.as_bytes());
    }
    
    #[test]
    fn test_different_salt_different_key() {
        let password = b"test_password";
        let salt1 = generate_salt();
        let salt2 = generate_salt();
        let params = KeyDerivationParams::fast();
        
        let key1 = derive_key(password, &salt1, &params).unwrap();
        let key2 = derive_key(password, &salt2, &params).unwrap();
        
        assert_ne!(key1.as_bytes(), key2.as_bytes());
    }
    
    #[test]
    fn test_different_password_different_key() {
        let password1 = b"password1";
        let password2 = b"password2";
        let salt = generate_salt();
        let params = KeyDerivationParams::fast();
        
        let key1 = derive_key(password1, &salt, &params).unwrap();
        let key2 = derive_key(password2, &salt, &params).unwrap();
        
        assert_ne!(key1.as_bytes(), key2.as_bytes());
    }
}
