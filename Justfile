# List all available commands
default:
    @just --list

# =============================================================================
# DEVELOPMENT
# =============================================================================

# Run the Desktop App (Tauri + React) - Manish + OmmPrakash
dev-desktop:
    @echo "Starting Identra Desktop App..."
    cd clients/ghost-desktop && yarn install && yarn tauri dev

# Run the Tunnel Gateway (Rust gRPC Service) - Sarthak
dev-gateway:
    @echo "Starting Tunnel Gateway..."
    cargo run --bin tunnel-gateway

# Run the Local Vault Daemon (Rust Secure Storage) - Sarthak
dev-vault:
    @echo "Starting Vault Daemon..."
    cargo run --bin vault-daemon

# Run the Brain Service (Python FastAPI + RAG) - Sailesh
dev-brain:
    @echo "Starting Brain Service..."
    cd apps/brain-service && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && python main.py

# Run all backend services in parallel (Gateway + Vault + Brain)
dev-backend:
    @echo "Starting all backend services..."
    just dev-gateway & just dev-vault & just dev-brain

# Run the entire stack (Database + Backend + Desktop)
dev-all:
    @echo "Starting full Identra stack..."
    just db-up
    @sleep 2
    just dev-backend &
    @sleep 1
    just dev-desktop

# =============================================================================
# BUILD & COMPILATION
# =============================================================================

# Check if all Rust code compiles
check:
    @echo "Checking Rust workspace..."
    cargo check --workspace

# Build all Rust components
build:
    @echo "Building Rust workspace..."
    cargo build --workspace

# Build Rust components in release mode
build-release:
    @echo "Building Rust workspace (release mode)..."
    cargo build --workspace --release

# Build the shared Rust libraries only
build-libs:
    @echo "Building shared libraries..."
    cargo build --lib -p identra-core
    cargo build --lib -p identra-crypto
    cargo build --lib -p identra-proto
    cargo build --lib -p identra-auth

# Build the Desktop App for production
build-desktop:
    @echo "Building Desktop App..."
    cd clients/ghost-desktop && yarn install && yarn tauri build

# Build proto files (gRPC definitions)
build-proto:
    @echo "Building protobuf definitions..."
    cargo build -p identra-proto

# =============================================================================
# TESTING
# =============================================================================

# Run all Rust tests
test:
    @echo "Running Rust tests..."
    cargo test --workspace

# Run tests with coverage
test-coverage:
    @echo "Running tests with coverage..."
    cargo tarpaulin --workspace --out Html --output-dir coverage

# Run integration tests only
test-integration:
    @echo "Running integration tests..."
    cargo test --workspace -- --ignored

# Test the authentication flow
test-auth:
    @echo "Testing authentication..."
    cd apps/tunnel-gateway && cargo test auth

# =============================================================================
# DATABASE & INFRASTRUCTURE
# =============================================================================

# Start local Postgres + pgvector database
db-up:
    @echo "Starting Postgres database..."
    docker run --name identra-db -e POSTGRES_PASSWORD=password -d -p 5432:5432 pgvector/pgvector:pg16 || echo "Database already running"

# Stop the database
db-down:
    @echo "Stopping Postgres database..."
    docker stop identra-db || true
    docker rm identra-db || true

# Reset database (stop, remove, restart)
db-reset:
    @echo "Resetting database..."
    just db-down
    just db-up

# Access database shell
db-shell:
    @echo "Connecting to database..."
    docker exec -it identra-db psql -U postgres

# =============================================================================
# LINTING & FORMATTING
# =============================================================================

# Format all Rust code
fmt:
    @echo "Formatting Rust code..."
    cargo fmt --all

# Check Rust formatting
fmt-check:
    @echo "Checking Rust formatting..."
    cargo fmt --all -- --check

# Run Clippy linter
lint:
    @echo "Running Clippy..."
    cargo clippy --workspace -- -D warnings

# Fix linting issues automatically
lint-fix:
    @echo "Fixing linting issues..."
    cargo clippy --workspace --fix --allow-dirty

# Format and lint everything
format-all:
    @echo "Formatting and linting..."
    just fmt
    just lint

# =============================================================================
# CLEANUP
# =============================================================================

# Clean all build artifacts
clean:
    @echo "Cleaning build artifacts..."
    cargo clean
    cd clients/ghost-desktop && rm -rf dist node_modules
    cd apps/brain-service && rm -rf .venv __pycache__

# Deep clean (including dependencies)
clean-deep:
    @echo "Deep cleaning..."
    just clean
    rm -rf target/
    rm -rf clients/ghost-desktop/src-tauri/target/

# =============================================================================
# DEPENDENCIES
# =============================================================================

# Update all Rust dependencies
update-deps:
    @echo "Updating Rust dependencies..."
    cargo update

# Install Desktop App dependencies
install-desktop:
    @echo "Installing Desktop App dependencies..."
    cd clients/ghost-desktop && yarn install

# Install Brain Service dependencies
install-brain:
    @echo "Installing Brain Service dependencies..."
    cd apps/brain-service && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# Install all dependencies
install-all:
    @echo "Installing all dependencies..."
    just install-desktop
    just install-brain

# =============================================================================
# UTILITIES
# =============================================================================

# Show workspace structure
tree:
    @echo "Workspace structure:"
    @tree -L 3 -I 'node_modules|target|.git'

# Show current status
status:
    @echo "Identra Status:"
    @echo "  - Desktop App: clients/ghost-desktop/"
    @echo "  - Tunnel Gateway: apps/tunnel-gateway/"
    @echo "  - Vault Daemon: apps/vault-daemon/"
    @echo "  - Brain Service: apps/brain-service/"
    @echo "  - Shared Libraries: libs/"
    @cargo --version
    @rustc --version

# Generate documentation
docs:
    @echo "Generating documentation..."
    cargo doc --workspace --no-deps --open

# Watch for changes and rebuild
watch:
    @echo "Watching for changes..."
    cargo watch -x check -x test

# =============================================================================
# PRODUCTION DEPLOYMENT (Arpit)
# =============================================================================

# Build for production
prod-build:
    @echo "Building for production..."
    just build-release
    just build-desktop

# Run pre-deployment checks
prod-check:
    @echo "Running pre-deployment checks..."
    just fmt-check
    just lint
    just test
    just build-release
