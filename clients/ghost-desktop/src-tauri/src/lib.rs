pub mod commands;
pub mod state;

use crate::commands::*;
use crate::state::NexusState;
use tauri::Manager;
use tauri_plugin_global_shortcut::{Code, Modifiers, ShortcutState, Shortcut};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(NexusState::new())
        .plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_shortcut(Shortcut::new(Some(Modifiers::ALT), Code::Space))
                .unwrap()
                // CHANGE: .on_shortcut -> .with_handler
                .with_handler(|app, shortcut, event| {
                    if event.state == ShortcutState::Pressed {
                        if shortcut.matches(Modifiers::ALT, Code::Space) {
                            if let Some(launcher) = app.get_webview_window("launcher") {
                                if launcher.is_visible().unwrap_or(false) {
                                    let _ = launcher.hide();
                                } else {
                                    let _ = launcher.show();
                                    let _ = launcher.set_focus();
                                }
                            }
                        }
                    }
                })
                .build(),
        )
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