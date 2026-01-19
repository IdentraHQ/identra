fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Compile proto files (output goes to OUT_DIR by default)
    tonic_build::configure()
        .build_server(true)
        .build_client(true)
        .compile_protos(
            &[
                "proto/vault.proto",
                "proto/memory.proto",
                "proto/health.proto",
                "proto/auth.proto",
            ],
            &["proto"],
        )?;
    
    Ok(())
}
