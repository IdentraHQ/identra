pub mod commands;
pub mod grpc_client;
pub mod ipc_client;
pub mod state;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Load environment variables from .env file
    let _ = dotenvy::dotenv();
    
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        // Initialize AI & State Management
        .manage(commands::AIState::new())
        .manage(state::NexusState::new())
        // Register Commands
        .invoke_handler(tauri::generate_handler![
            // --- System ---
            commands::get_system_status,
            commands::toggle_launcher,
            commands::toggle_main_window,
            
            // --- Auth & Session ---
            commands::initialize_session,
            commands::login_user,
            commands::register_user,
            
            // --- Memory & Intelligence ---
            commands::vault_memory,     // Store
            commands::decrypt_memory,   // Retrieve (Secrets)
            commands::query_history,    // Query (Legacy/Search)
            commands::semantic_search,  // Vector Search
            commands::fetch_history,    // Recent History
            commands::chat_with_ai,     // AI Chat (NEW)
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}