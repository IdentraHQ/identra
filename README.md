# Identra

Identra is a confidential operating system layer designed to act as a unified **Identity and Memory Vault** for AI interactions. It solves AI fragmentation by providing a single, secure source of truth that travels with the user across different AI tools.

The system functions as a **Fortified Library** between the User and External AI, utilizing local-first vectorization, encrypted storage, and secure compute enclaves.

---

## Architecture Overview

This repository is a **Rust Workspace Monorepo** managing the entire Identra stack:

- **The Nexus (Desktop):** Rust + Tauri v2  
  Handles local state, global hotkeys, and system hooks.

- **The View (UI):** React (Next.js) + Shadcn UI  
  Static frontend running inside the Tauri WebView.

- **The Tunnel (Gateway):** Rust (Axum / Tonic)  
  High-performance gRPC gateway for all external communication.

- **The Vault (Security):** Rust + OS Keychain Integration  
  Local secure daemon for cryptographic key management (MVP uses OS-native secure storage; AWS Nitro Enclaves planned for production).

- **The Brain (RAG):** Python (FastAPI)  
  Isolated AI service responsible for RAG orchestration and inference.

---

## Repository Structure & Team Assignments

Strict adherence to these folder ownership rules is **mandatory** to avoid merge conflicts and architectural drift.

```text
identra/
├── apps/                               # Backend Services
│   ├── tunnel-gateway/                 # OWNER: Sarthak (Rust gRPC Entry Point)
│   ├── vault-daemon/                   # OWNER: Sarthak (Local Secure Vault - MVP uses OS keychain)
│   └── brain-service/                  # OWNER: Sailesh (Python RAG & AI Logic)
│
├── clients/                            # Frontend & Desktop
│   └── ghost-desktop/
│       ├── src-tauri/                  # OWNER: Manish (Rust Backend / System Architecture)
│       └── src/                        # OWNER: OmmPrakash (React / Next.js UI)
│
├── libs/                               # Shared Libraries
│   ├── identra-core/                   # SHARED: Manish / Sarthak (Errors, Logging)
│   ├── identra-crypto/                 # SHARED: Manish / Sarthak (Encryption Primitives)
│   ├── identra-proto/                  # SHARED: Manish / Sarthak (gRPC Protobufs)
│   └── identra-auth/                   # SHARED: Manish (OIDC / Auth Logic)
│
├── infra/                              # OWNER: Arpit (Terraform, Kubernetes, AWS)
├── tools/                              # OWNER: Arpit (Dev Scripts, Docker)
├── Cargo.toml                          # Rust Workspace Configuration
└── Justfile                            # Unified Command Runner
```

## Critical Git Protocol

To maintain a clean Git history and avoid rebasing conflicts, every contributor must follow this workflow.

- Rule 1: Always Pull Before Coding. Never start work without syncing with the remote repository.

- Rule 2: Never Commit Directly to main. Use feature branches for any non-trivial work.

## Safe Git Workflow

- Start Your Session

- Run immediately when opening a terminal:

```
git checkout main
git pull origin main
```

- Create a Feature Branch (Recommended)

```
git checkout -b feature/your-feature-name
```

- Make Changes

Modify only files inside your assigned directories.

Do not refactor or touch unrelated modules.

- Commit Changes

```
git add .
git commit -m "feat: concise description of changes"
```

Sync Before Pushing

```
git pull origin main --rebase
```

Push Changes

```
git push origin branch-name
```

## Development Setup

We use Just as the unified task runner.

Prerequisites

- Rust (latest stable)
- Node.js (LTS)
- Yarn
- Docker

Quick Start
Install Dependencies

# Rust workspace dependencies

cargo build

# Frontend dependencies

cd clients/ghost-desktop
yarn install

Running Services
Desktop App (Manish, OmmPrakash)
just dev-desktop

Backend Gateway (Sarthak)
just dev-gateway

Infrastructure & Databases (Arpit)
just db-up

Design Principles

Local-first by default

Zero-trust security model

Explicit boundaries between AI, memory, and identity

Deterministic state over opaque AI behavior

Rust for safety-critical paths

## MVP Architecture Note

**For the initial MVP release, we are using local OS-native secure storage instead of AWS Nitro Enclaves:**

- **Vault Security:** OS Keychain (Windows Credential Manager/DPAPI, macOS Keychain, Linux Secret Service)
- **Data Storage:** Local encrypted SQLite with SQLCipher
- **Process Isolation:** Separate Rust daemon process with memory locking
- **Future:** AWS Nitro Enclaves integration planned for production cloud deployment

This approach allows rapid MVP development while maintaining strong local security boundaries.
┌─────────────────────────┐
│  Desktop App (Tauri)    │
│  clients/ghost-desktop  │
└───────────┬─────────────┘
            │ IPC (encrypted)
┌───────────▼─────────────┐
│  Local Vault Daemon     │
│  apps/vault-daemon      │
│  ├─ OS Keychain         │
│  ├─ Memory Encryption   │
│  └─ Locked Memory       │
└───────────┬─────────────┘
            │
┌───────────▼─────────────┐
│  Local SQLite DB        │
│  (Encrypted with SQLCipher)
└─────────────────────────┘
License

Proprietary. All rights reserved.
