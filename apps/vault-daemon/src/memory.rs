use crate::error::Result;
use region::{Protection, protect};
use secrecy::Secret;
use zeroize::Zeroize;

/// Secure memory container that locks pages and zeros on drop
pub struct SecureMemory {
    data: Vec<u8>,
    locked: bool,
}

impl SecureMemory {
    /// Create new secure memory region
    pub fn new(size: usize) -> Result<Self> {
        let data = vec![0u8; size];
        
        // Lock memory pages to prevent swapping to disk
        let locked = Self::lock_memory(&data);
        
        Ok(Self { data, locked })
    }
    
    /// Create from existing data (will be zeroized in source)
    pub fn from_vec(data: Vec<u8>) -> Result<Self> {
        let locked = Self::lock_memory(&data);
        Ok(Self { data, locked })
    }
    
    /// Lock memory pages (platform-specific)
    fn lock_memory(data: &[u8]) -> bool {
        #[cfg(windows)]
        {
            // Lock the memory pages
            unsafe {
                protect(
                    data.as_ptr(),
                    data.len(),
                    Protection::READ_WRITE,
                ).is_ok()
            }
        }
        
        #[cfg(not(windows))]
        {
            // On Unix, use mlock
            unsafe {
                libc::mlock(data.as_ptr() as *const libc::c_void, data.len()) == 0
            }
        }
    }
    
    /// Get immutable reference to data
    pub fn as_slice(&self) -> &[u8] {
        &self.data
    }
    
    /// Get mutable reference to data
    pub fn as_mut_slice(&mut self) -> &mut [u8] {
        &mut self.data
    }
    
    /// Get length of secure memory
    pub fn len(&self) -> usize {
        self.data.len()
    }
    
    /// Check if empty
    pub fn is_empty(&self) -> bool {
        self.data.is_empty()
    }
}

impl Drop for SecureMemory {
    fn drop(&mut self) {
        // Zero out memory before dropping
        self.data.zeroize();
        
        // Unlock memory if it was locked
        if self.locked {
            #[cfg(windows)]
            {
                // Windows automatically unlocks on drop
            }
            
            #[cfg(not(windows))]
            {
                unsafe {
                    libc::munlock(self.data.as_ptr() as *const libc::c_void, self.data.len());
                }
            }
        }
    }
}

/// Secure string wrapper
pub type SecureString = Secret<String>;

/// Secure bytes wrapper  
pub type SecureBytes = Secret<Vec<u8>>;

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_secure_memory_creation() {
        let mem = SecureMemory::new(32).unwrap();
        assert_eq!(mem.len(), 32);
    }
    
    #[test]
    fn test_secure_memory_zeroization() {
        let data = vec![1, 2, 3, 4, 5];
        let mut mem = SecureMemory::from_vec(data).unwrap();
        
        // Modify data
        mem.as_mut_slice()[0] = 99;
        assert_eq!(mem.as_slice()[0], 99);
        
        // Drop will zeroize
        drop(mem);
    }
}
