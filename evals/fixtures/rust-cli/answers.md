# Canned interview answers — rust-cli fixture

1. **Project description:** greet is a command-line greeter: invoked as
   `greet <name>`, it prints `Hello, <name>!` and exits. One cargo binary,
   consumed by people at a shell prompt.
2. **Domain terms:** Greeting (the output line), Recipient (the name argument),
   Salutation (the fixed `Hello` prefix), Invocation (one run of the binary),
   Exit Status (the process result). No recurring wrong names yet — leave the
   debt column empty.
3. **Vocabulary polarity:** embrace — it is a product; use domain terms freely.
4. **API surface:** none. A plain CLI; no HTTP, no RPC, no public library API.
5. **Gate commands:** none beyond the stack defaults you detected — use
   `cargo clippy`, `cargo test`, `cargo build`.
6. **Parallel agents:** no — solo development on this machine.
7. **Unit of work:** not applicable — plain CLI, no Logging section.
8. **First epic:** Epic 0 — Ship the greeter (greet builds, greets, and is
   gated).
