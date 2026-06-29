---
name: debug
description: Use when debugging a crash, hang, wrong result, or memory fault in native code (C/C++/Rust/Swift) by driving lldb — setting breakpoints, stepping, and inspecting frames, variables, and memory to localize the fault. gdb is a documented sibling.
---

# Debug

Drive `lldb` to find *why* a native program misbehaves — localize the faulting line and the
state that proves it; don't guess from the source. The agent runs `lldb` through the shell, so prefer **batch mode** over the interactive prompt.

**Scope.** The debugger tool, not the lifecycle. Use the `code` skill's bug-fix path to
*frame and fix* a bug; reach for `debug` when localizing a fault in a compiled binary or core
needs breakpoints and runtime inspection. Generic debugger practice — no glossary row; it reuses no coined Foundry terms.

## Drive lldb non-interactively

The agent has no interactive TTY, so script the session: `-o` runs one command per
flag, `-s <file>` runs a command file, and `-b`/`--batch` runs then exits.

    lldb --batch -o 'b buggy.c:12' -o 'run' -o 'bt' -o 'frame variable' -o 'quit' -- ./buggy

Build with debug info first (`cc -g -O0`); optimized binaries hide locals and inline
frames. The full command set is in [`references/lldb.md`](references/lldb.md).

## The loop

1. **Reproduce + load.** Build `-g -O0`. `lldb ./bin` to launch, `lldb -p <pid>` to
   attach to a running process, or `lldb -c core ./bin` to open a core dump.
2. **Break.** Set a breakpoint at the suspect site — `b <file>:<line>`, `b <symbol>`,
   or a **conditional** `br set -f buggy.c -l 12 -c 'i == n'` to stop only at the bad
   iteration. For a bad write, a **watchpoint** `w set var buf` stops on change.
3. **Run.** `run` (or `process launch`). On a crash lldb stops at the fault with a
   `stop reason` (e.g. `EXC_BAD_ACCESS`, `signal SIGABRT`).
4. **Inspect.** `bt` for the call stack; `frame select <n>` to move; `frame variable`
   or `p <expr>` to read locals; `x/8xw <addr>` for memory; `register read`.
5. **Step.** `next` (over), `step` (into), `finish` (out), `continue` (to next stop).
6. **Localize.** Name the faulting `file:line`, the offending expression, and the
   state that proves it (e.g. `i == 8` writing past an 8-element buffer). That
   evidence — breakpoint hit, state inspected, line named — is the deliverable.

## References

- [`references/lldb.md`](references/lldb.md) — the full `lldb` command cheatsheet
  (launch/attach/core, breakpoints, watchpoints, execution, inspection, stop reasons).
- [`references/gdb-map.md`](references/gdb-map.md) — the same workflow in `gdb`.
- [`references/walkthrough.md`](references/walkthrough.md) — a seeded out-of-bounds
  write localized end to end with `lldb`.
