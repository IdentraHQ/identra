# Identra AI Coding Agent Instructions

## Project Overview

Identra is a **Rust Workspace Monorepo** building a confidential AI identity and memory vault. The system has 5 core components:

1. **The Nexus (Desktop):** Tauri v2 app in `clients/ghost-desktop/src-tauri/` - system hooks, global shortcuts, local state
2. **The View (UI):** React + Vite in `clients/ghost-desktop/src/` - WebView frontend with Tailwind CSS
3. **The Tunnel (Gateway):** Rust gRPC service in `apps/tunnel-gateway/` - external communication gateway
4. **The Vault (Security):** Local Rust daemon in `apps/vault-daemon/` - OS keychain integration, memory encryption (MVP uses local secure storage; AWS Nitro Enclaves planned for production)
5. **The Brain (RAG):** Python FastAPI service in `apps/brain-service/` - AI/RAG orchestration

## Critical File Ownership Rules

**NEVER modify files outside your assigned domain without explicit permission:**

- **Manish:** `clients/ghost-desktop/src-tauri/`, shared libs coordination
- **OmmPrakash:** `clients/ghost-desktop/src/` (React/UI only)
- **Sarthak:** `apps/tunnel-gateway/`, `apps/vault-daemon/`, shared libs
- **Sailesh:** `apps/brain-service/`
- **Arpit:** `infra/`, `tools/`

## Architecture Patterns

### Tauri Desktop App Structure

The desktop app follows a **window-per-purpose** pattern:

- **Main window** (`main`): Primary UI, hides on close (doesn't exit)
- **Launcher window** (`launcher`): Spotlight-like overlay (CMD+K), always-on-top, frameless

See [src-tauri/src/lib.rs](clients/ghost-desktop/src-tauri/src/lib.rs#L34-L49) for window initialization.

### Tauri Command Pattern

Commands use async Rust with `State` injection:

```rust
#[tauri::command]
pub async fn get_system_status(state: State<'_, NexusState>) -> Result<SystemStatusResponse, String> {
    let status = state.status.lock().map_err(|_| "State mutex poisoned")?.clone();
    // ... implementation
}
```

Register in [lib.rs](clients/ghost-desktop/src-tauri/src/lib.rs#L13-L17) via `invoke_handler!`.

### Shared Library Usage

Import workspace libraries in `Cargo.toml`:

```toml
identra-core = { path = "../../../libs/identra-core" }
identra-crypto = { path = "../../../libs/identra-crypto" }
identra-proto = { path = "../../../libs/identra-proto" }
```

All apps/libraries are unified in the root [Cargo.toml](Cargo.toml) workspace.

## Development Workflows

### Task Runner: Just

**Always use `just` commands** (defined in [Justfile](Justfile)):

- `just dev-desktop` - Run Tauri desktop app (hot-reload enabled)
- `just dev-gateway` - Run tunnel-gateway service
- `just check` - Verify all Rust code compiles
- `just build-libs` - Build shared libraries only
- `just db-up` - Start local Postgres + pgvector

### Desktop Development

From `clients/ghost-desktop/`:
```bash
yarn tauri dev  # or `just dev-desktop` from root
```

Frontend uses Vite with React 19. Tauri automatically rebuilds Rust on changes.

### Adding Tauri Commands

1. Define in [commands.rs](clients/ghost-desktop/src-tauri/src/commands.rs)
2. Register in [lib.rs](clients/ghost-desktop/src-tauri/src/lib.rs#L13) `invoke_handler!` macro
3. Call from React via `@tauri-apps/api`

### State Management (Tauri)

Global state lives in [state.rs](clients/ghost-desktop/src-tauri/src/state.rs). Uses `Mutex` for thread-safe access:

```rust
pub struct NexusState {
    pub status: Mutex<VaultStatus>,
    pub active_identity: Mutex<Option<String>>,
    pub metrics: Mutex<EnclaveMetrics>,
}
```

Inject via `State<'_, NexusState>` in commands.

## Git Workflow (MANDATORY)

**Never commit to `main` directly.** Always:

```bash
git checkout main && git pull origin main
git checkout -b feature/your-feature
# ... make changes ...
git add .
git commit -m "feat: description"
git pull origin main --rebase
git push origin feature/your-feature
```

## Build Configuration

### Rust Release Profile

Optimized for binary size ([Cargo.toml](Cargo.toml#L14-L17)):

```toml
[profile.release]
lto = true          # Link-time optimization
strip = true        # Strip debug symbols
codegen-units = 1   # Single codegen unit for better optimization
```

### Tauri Build

Desktop app uses `staticlib`, `cdylib`, and `rlib` crate types for Tauri compatibility.

## External Dependencies

- **Database:** Postgres + pgvector (run via `just db-up`)
- **OS Keychain:** Windows Credential Manager/DPAPI, macOS Keychain, Linux Secret Service
- **AI Services:** Expected to call external LLM APIs (not yet implemented)
- **AWS Nitro:** Planned for production; MVP uses local vault-daemon with OS keychain

## Technology Stack Summary

| Component | Language | Framework | Key Libraries |
|-----------|----------|-----------|---------------|
| Desktop Backend | Rust | Tauri v2 | serde, uuid, tokio |
| Desktop Frontend | JavaScript | React 19 + Vite | lucide-react, Tailwind CSS |
| Gateway | Rust | Axum/Tonic (planned) | - |
| Vault Daemon | Rust | OS Keychain + IPC | keyring, secrecy, zeroize |
| Brain | Python | FastAPI | - |

## Common Pitfalls

1. **Editing outside your domain:** Respect ownership boundaries to avoid merge conflicts
2. **Direct `main` commits:** Always use feature branches
3. **Manual commands instead of `just`:** Prefer Justfile recipes for consistency
4. **Forgetting window behavior:** Main window hides (doesn't close) - see [window event handler](clients/ghost-desktop/src-tauri/src/lib.rs#L28-L32)
5. **Mutex poisoning:** Always handle `.lock()` errors in Tauri state access

## Next Steps for Implementation

Several components are scaffolded but not implemented:

- gRPC services in `tunnel-gateway` (Axum + Tonic integration)
- Local vault-daemon with OS keychain integration in `vault-daemon`
- IPC communication layer between Tauri and vault-daemon
- Python RAG logic in `brain-service` (only FastAPI imported)
- Shared library functionality in `libs/` (currently placeholder code)
- Database persistence layer with encrypted SQLite

When implementing, follow the established patterns above and consult team ownership rules.
