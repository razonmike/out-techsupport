fn main() {
    // OUT-TECHSUPPORT: brand values are baked in via option_env! at compile time.
    // Cargo does NOT rebuild when an env var changes unless told to watch it, so a
    // cached build from another brand would keep the previous APP_NAME/key/password.
    for var in [
        "OTS_APP_NAME",
        "OTS_RENDEZVOUS",
        "OTS_API_SERVER",
        "OTS_SERVER_KEY",
        "OTS_CLIENT_PASSWORD",
    ] {
        println!("cargo:rerun-if-env-changed={}", var);
    }

    let out_dir = format!("{}/protos", std::env::var("OUT_DIR").unwrap());

    std::fs::create_dir_all(&out_dir).unwrap();

    protobuf_codegen::Codegen::new()
        .pure()
        .out_dir(out_dir)
        .inputs(["protos/rendezvous.proto", "protos/message.proto"])
        .include("protos")
        .customize(protobuf_codegen::Customize::default().tokio_bytes(true))
        .run()
        .expect("Codegen failed.");
}
