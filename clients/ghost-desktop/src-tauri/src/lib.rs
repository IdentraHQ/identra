mod state;
mod commands;

use tauri::{Manager, WebviewWindowBuilder};
use state::NexusState;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(NexusState::new())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .invoke_handler(tauri::generate_handler![
            commands::get_system_status,
            commands::vault_memory,
            commands::toggle_launcher,
            commands::toggle_main_window
        ])
        .setup(|app| {
            let main_window = app.get_webview_window("main").unwrap();
            
            #[cfg(debug_assertions)]
            main_window.open_devtools();

            // Handle window close -> hide to tray/background
            let main_window_clone = main_window.clone();
            main_window.on_window_event(move |event| {
                if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                    let _ = main_window_clone.hide();
                    api.prevent_close();
                }
            });

            // Init Launcher Window (Spotlight/Raycast alternative)
            let _launcher = WebviewWindowBuilder::new(
                app,
                "launcher",
                tauri::WebviewUrl::App("launcher.html".into())
            )
            .title("Identra Launcher")
            .inner_size(800.0, 600.0)
            .center()
            .resizable(false)
            .decorations(false)
            .transparent(true)
            .always_on_top(true)
            .skip_taskbar(true)
            .visible(false)
            .build()
            .expect("Failed to initialize launcher surface");

            // Register Global Hotkey (Alt+Space)
            use tauri_plugin_global_shortcut::{GlobalShortcutExt, Code, Modifiers, Shortcut};
            let shortcut = Shortcut::new(Some(Modifiers::ALT), Code::Space);
            
            app.global_shortcut().on_shortcut(shortcut, move |handle, _, _| {
                if let Some(launcher) = handle.get_webview_window("launcher") {
                    if launcher.is_visible().unwrap_or(false) {
                        let _ = launcher.hide();
                    } else {
                        let _ = launcher.show();
                        let _ = launcher.set_focus();
                    }
                }
            }).expect("Global shortcut registration failed");
            
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("Identra Nexus runtime failure");
}