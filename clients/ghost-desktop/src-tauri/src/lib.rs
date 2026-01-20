pub mod commands;
pub mod state;
pub mod grpc_client;

use crate::commands::*;
use crate::state::NexusState;
use tauri_plugin_global_shortcut::{Code, Modifiers, Shortcut, ShortcutState, GlobalShortcutExt};

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
            decrypt_memory,
            query_history
        ])
        .setup(|app| {
            println!("Setting up global shortcut for Alt+Space");
            
            // Create shortcut using Code and Modifiers
            let shortcut = Shortcut::new(Some(Modifiers::ALT), Code::Space);
            let handle = app.handle().clone();
            
            // Build and register the plugin with the shortcut
            let plugin = tauri_plugin_global_shortcut::Builder::new()
                .with_handler(move |app, shortcut, event| {
                    println!("Shortcut triggered! Event: {:?}", event);
                    if event.state == ShortcutState::Pressed {
                        let handle_clone = handle.clone();
                        tauri::async_runtime::spawn(async move {
                            match toggle_launcher(handle_clone).await {
                                Ok(_) => println!("Launcher toggled successfully"),
                                Err(e) => println!("Error toggling launcher: {}", e),
                            }
                        });
                    }
                })
                .build();
            
            app.handle().plugin(plugin)?;
            
            // Register the shortcut
            app.global_shortcut().register(shortcut)?;
            println!("Alt+Space registered successfully");
            
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}