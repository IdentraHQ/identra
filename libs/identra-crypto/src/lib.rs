use aes_gcm::{
    Aes256Gcm,
    Key,
    Nonce,
    // ADDED: AeadCore (This fixes the generate_nonce error)
    aead::{Aead, AeadCore, KeyInit, OsRng}, 
};
use base64::{Engine as _, engine::general_purpose::STANDARD as BASE64};

pub struct MemoryVault;

// Define a simple result alias for cleaner code
type Result<T> = std::result::Result<T, String>;

impl MemoryVault {
    /// Generates a cryptographically secure 256-bit key
    pub fn generate_key() -> Key<Aes256Gcm> {
        Aes256Gcm::generate_key(&mut OsRng)
    }

    /// Encrypts a string into a Base64 packet (Nonce + Ciphertext)
    pub fn lock(data: &str, key: &Key<Aes256Gcm>) -> Result<String> {
        let cipher = Aes256Gcm::new(key);
        // This line requires AeadCore to be imported
        let nonce = Aes256Gcm::generate_nonce(&mut OsRng); 

        let ciphertext = cipher.encrypt(&nonce, data.as_bytes())
            .map_err(|_| "Encryption failed".to_string())?;

        // Combine Nonce + Ciphertext
        let mut packet = Vec::with_capacity(nonce.len() + ciphertext.len());
        packet.extend_from_slice(&nonce);
        packet.extend_from_slice(&ciphertext);

        // Return as Base64 string
        Ok(BASE64.encode(packet))
    }

    /// Decrypts a Base64 string back into plaintext using the provided session key.
    pub fn open(enc_packet: &str, key: &Key<Aes256Gcm>) -> Result<String> {
        // 1. Decode Base64
        let packet_bytes = BASE64.decode(enc_packet)
            .map_err(|e| format!("Base64 decode failed: {}", e))?;

        // 2. Extract Nonce (First 12 bytes) and Ciphertext
        if packet_bytes.len() < 12 {
            return Result::Err("Packet too short".to_string());
        }
        let (nonce_bytes, ciphertext) = packet_bytes.split_at(12);
        let nonce = Nonce::from_slice(nonce_bytes);

        // 3. Init Cipher
        let cipher = Aes256Gcm::new(key);

        // 4. Decrypt
        let plaintext_bytes = cipher.decrypt(nonce, ciphertext)
            .map_err(|_| "Decryption failed (Wrong Key or Corrupted Data)".to_string())?;

        // 5. Convert to String
        String::from_utf8(plaintext_bytes)
            .map_err(|e| format!("UTF-8 Error: {}", e))
    }
}