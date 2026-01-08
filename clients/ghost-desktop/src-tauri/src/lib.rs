pub mod commands;
pub mod state;

use crate::commands::*;
use crate::state::NexusState;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(NexusState::new())
        .invoke_handler(tauri::generate_handler![
            toggle_launcher,
            toggle_main_window,
            get_system_status,
            initialize_session, 
            vault_memory,       
            decrypt_memory      
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}