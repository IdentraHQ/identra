use crate::error::{CryptoError, Result};
use crate::{KEY_SIZE, NONCE_SIZE};
use chacha20poly1305::{
    aead::{Aead, KeyInit, OsRng},
    ChaCha20Poly1305, Key, Nonce as ChaNonce,
};
use zeroize::Zeroize;

/// Encryption key wrapper
#[derive(Clone, Zeroize)]
#[zeroize(drop)]
pub struct EncryptionKey([u8; KEY_SIZE]);

impl EncryptionKey {
    /// Create a new encryption key from bytes
    pub fn from_bytes(bytes: &[u8]) -> Result<Self> {
        if bytes.len() != KEY_SIZE {
            return Err(CryptoError::InvalidKeyLength {
                expected: KEY_SIZE,
                actual: bytes.len(),
            });
        }
        
        let mut key = [0u8; KEY_SIZE];
        key.copy_from_slice(bytes);
        Ok(Self(key))
    }
    
    /// Get key as bytes
    pub fn as_bytes(&self) -> &[u8] {
        &self.0
    }
    
    /// Generate a random key
    pub fn generate() -> Self {
        let mut key = [0u8; KEY_SIZE];
        getrandom::getrandom(&mut key).expect("Failed to generate random key");
        Self(key)
    }
}

/// Nonce wrapper
#[derive(Clone)]
pub struct Nonce([u8; NONCE_SIZE]);

impl Nonce {
    /// Create a new nonce from bytes
    pub fn from_bytes(bytes: &[u8]) -> Result<Self> {
        if bytes.len() != NONCE_SIZE {
            return Err(CryptoError::InvalidNonceLength {
                expected: NONCE_SIZE,
                actual: bytes.len(),
            });
        }
        
        let mut nonce = [0u8; NONCE_SIZE];
        nonce.copy_from_slice(bytes);
        Ok(Self(nonce))
    }
    
    /// Get nonce as bytes
    pub fn as_bytes(&self) -> &[u8] {
        &self.0
    }
    
    /// Generate a random nonce
    pub fn generate() -> Self {
        let mut nonce = [0u8; NONCE_SIZE];
        getrandom::getrandom(&mut nonce).expect("Failed to generate random nonce");
        Self(nonce)
    }
}

/// Encrypt data using ChaCha20-Poly1305
///
/// # Arguments
/// * `key` - Encryption key (32 bytes)
/// * `nonce` - Nonce for encryption (12 bytes, must be unique per message)
/// * `plaintext` - Data to encrypt
///
/// # Returns
/// Encrypted ciphertext with authentication tag
pub fn encrypt(key: &EncryptionKey, nonce: &Nonce, plaintext: &[u8]) -> Result<Vec<u8>> {
    let cipher_key = Key::from_slice(key.as_bytes());
    let cipher = ChaCha20Poly1305::new(cipher_key);
    let cipher_nonce = ChaNonce::from_slice(nonce.as_bytes());
    
    cipher
        .encrypt(cipher_nonce, plaintext)
        .map_err(|e| CryptoError::Encryption(e.to_string()))
}

/// Decrypt data using ChaCha20-Poly1305
///
/// # Arguments
/// * `key` - Decryption key (32 bytes)
/// * `nonce` - Nonce used during encryption (12 bytes)
/// * `ciphertext` - Encrypted data with authentication tag
///
/// # Returns
/// Decrypted plaintext if authentication succeeds
pub fn decrypt(key: &EncryptionKey, nonce: &Nonce, ciphertext: &[u8]) -> Result<Vec<u8>> {
    let cipher_key = Key::from_slice(key.as_bytes());
    let cipher = ChaCha20Poly1305::new(cipher_key);
    let cipher_nonce = ChaNonce::from_slice(nonce.as_bytes());
    
    cipher
        .decrypt(cipher_nonce, ciphertext)
        .map_err(|e| CryptoError::Decryption(e.to_string()))
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_encrypt_decrypt() {
        let key = EncryptionKey::generate();
        let nonce = Nonce::generate();
        let plaintext = b"Hello, Identra!";
        
        let ciphertext = encrypt(&key, &nonce, plaintext).unwrap();
        assert_ne!(ciphertext.as_slice(), plaintext);
        
        let decrypted = decrypt(&key, &nonce, &ciphertext).unwrap();
        assert_eq!(decrypted.as_slice(), plaintext);
    }
    
    #[test]
    fn test_wrong_key_fails() {
        let key1 = EncryptionKey::generate();
        let key2 = EncryptionKey::generate();
        let nonce = Nonce::generate();
        let plaintext = b"Secret message";
        
        let ciphertext = encrypt(&key1, &nonce, plaintext).unwrap();
        
        // Decrypting with wrong key should fail
        let result = decrypt(&key2, &nonce, &ciphertext);
        assert!(result.is_err());
    }
    
    #[test]
    fn test_wrong_nonce_fails() {
        let key = EncryptionKey::generate();
        let nonce1 = Nonce::generate();
        let nonce2 = Nonce::generate();
        let plaintext = b"Secret message";
        
        let ciphertext = encrypt(&key, &nonce1, plaintext).unwrap();
        
        // Decrypting with wrong nonce should fail
        let result = decrypt(&key, &nonce2, &ciphertext);
        assert!(result.is_err());
    }
}
