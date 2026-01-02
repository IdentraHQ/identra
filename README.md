identra/
├── .github/                        # CI/CD Workflows (Rust Lint, Docker Build)
├── Cargo.toml                      # Workspace Definition
├── Justfile                        # Command Runner (like Make, but better)
│
├── infra/                          # Infrastructure as Code
│   ├── k8s/                        # Helm Charts for Kubernetes
│   ├── terraform/                  # AWS Provisioning (Nitro, RDS, VPC)
│   └── nitro/                      # Enclave Image (EIF) Dockerfiles
│
├── clients/                        # FRONTEND & DESKTOP
│   └── ghost-desktop/              # The Tauri Client
│       ├── src-tauri/              # Rust Backend (The Nexus)
│       │   ├── src/nexus.rs        # State Manager
│       │   ├── src/screener.rs     # Windows/Mac Accessibility Hooks
│       │   └── src/cortex.rs       # Local ONNX Runtime
│       └── src-ui/                 # Next.js Frontend (The View)
│           ├── app/overlay/        # Cmd+K Route
│           └── app/dashboard/      # Main Chat Route
│
├── apps/                           # BACKEND SERVICES
│   ├── tunnel-gateway/             # Rust gRPC Server (Entry Point)
│   │   └── src/main.rs             # Handles streams from Desktop
│   │
│   ├── enclave-service/            # Rust Secure Logic (Runs in Nitro)
│   │   └── src/kms.rs              # Key Management (The Vault)
│   │
│   └── brain-service/              # Python RAG Engine (The AI) <--- THE BRAIN
│       ├── main.py                 # FastAPI App
│       ├── rag_chain.py            # LangChain/LlamaIndex Logic
│       └── prompts/                # System Prompt Templates
│
├── libs/                           # SHARED RUST CRATES
│   ├── identra-core/               # Telemetry, Config, Errors
│   ├── identra-proto/              # Shared gRPC Definitions (.proto)
│   ├── identra-crypto/             # AES-256-GCM, Noise Protocol
│   └── identra-auth/               # OIDC/Hydra Integration
│
└── tools/                          # Developer Scripts
    ├── init_db.sh                  # Spin up local Postgres + pgvector
    └── mock_enclave.sh             # Run enclave logic locally for testing
