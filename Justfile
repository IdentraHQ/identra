# List all available commands
default:
    @just --list

# --- DEVELOPMENT ---

# Run the Desktop App (Manish + Omm)
dev-desktop:
    cd clients/ghost-desktop && yarn tauri dev

# Run the Backend Gateway (Sarthak)
dev-gateway:
    cargo run --bin tunnel-gateway

# Run the Local Vault Daemon (Sarthak)
dev-vault:
    cargo run --bin vault-daemon

# Check if everything compiles
check:
    cargo check --workspace

# --- INFRASTRUCTURE ---

# Spin up local database (Postgres + pgvector)
db-up:
    docker run --name identra-db -e POSTGRES_PASSWORD=password -d -p 5432:5432 pgvector/pgvector:pg16

# --- SYSTEMS ---

# Build the Rust Libraries only
build-libs:
    cargo build --lib -p identra-core
    cargo build --lib -p identra-crypto
