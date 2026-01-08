use crate::{KEY_SIZE, NONCE_SIZE, SALT_SIZE};
use crate::error::{CryptoError, Result};

/// Generate a random encryption key
pub fn generate_key() -> [u8; KEY_SIZE] {
    let mut key = [0u8; KEY_SIZE];
    getrandom::getrandom(&mut key)
        .expect("Failed to generate random key");
    key
}

/// Generate a random nonce
pub fn generate_nonce() -> [u8; NONCE_SIZE] {
    let mut nonce = [0u8; NONCE_SIZE];
    getrandom::getrandom(&mut nonce)
        .expect("Failed to generate random nonce");
    nonce
}

/// Generate a random salt for key derivation
pub fn generate_salt() -> [u8; SALT_SIZE] {
    let mut salt = [0u8; SALT_SIZE];
    getrandom::getrandom(&mut salt)
        .expect("Failed to generate random salt");
    salt
}

/// Generate random bytes of specified length
pub fn generate_random_bytes(length: usize) -> Vec<u8> {
    let mut bytes = vec![0u8; length];
    getrandom::getrandom(&mut bytes)
        .expect("Failed to generate random bytes");
    bytes
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_generate_key() {
        let key1 = generate_key();
        let key2 = generate_key();
        
        assert_eq!(key1.len(), KEY_SIZE);
        assert_eq!(key2.len(), KEY_SIZE);
        assert_ne!(key1, key2); // Should be different
    }
    
    #[test]
    fn test_generate_nonce() {
        let nonce1 = generate_nonce();
        let nonce2 = generate_nonce();
        
        assert_eq!(nonce1.len(), NONCE_SIZE);
        assert_eq!(nonce2.len(), NONCE_SIZE);
        assert_ne!(nonce1, nonce2); // Should be different
    }
    
    #[test]
    fn test_generate_salt() {
        let salt1 = generate_salt();
        let salt2 = generate_salt();
        
        assert_eq!(salt1.len(), SALT_SIZE);
        assert_eq!(salt2.len(), SALT_SIZE);
        assert_ne!(salt1, salt2); // Should be different
    }
    
    #[test]
    fn test_generate_random_bytes() {
        let bytes1 = generate_random_bytes(64);
        let bytes2 = generate_random_bytes(64);
        
        assert_eq!(bytes1.len(), 64);
        assert_eq!(bytes2.len(), 64);
        assert_ne!(bytes1, bytes2); // Should be different
    }
}
