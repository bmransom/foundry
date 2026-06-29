# lldb ↔ gdb command map

The [`debug`](../SKILL.md) workflow is identical under `gdb` — only the spelling
differs. `gdb` leads on most Linux toolchains (GCC); `lldb` leads on macOS / Clang /
Swift. For Rust on a gdb host, `rust-gdb` is the wrapper (the `rust-lldb` twin —
it loads the std pretty-printers; see [`lldb.md`](lldb.md)). Use this map to drive the
same loop with `gdb`.

## Driving non-interactively

`gdb` scripts with `-ex` (one command per flag) and `--batch` (run then exit):

    gdb --batch -ex 'b buggy.c:12' -ex 'run' -ex 'bt' -ex 'info locals' -ex 'quit' ./buggy

(lldb equivalent: `lldb --batch -o 'b buggy.c:12' -o run -o bt -o 'frame variable' -o quit -- ./buggy`)

## Command equivalents

| Goal | lldb | gdb |
|---|---|---|
| Launch | `lldb ./bin` → `run` | `gdb ./bin` → `run` |
| Attach to pid | `lldb -p <pid>` | `gdb -p <pid>` |
| Open a core | `lldb -c core ./bin` | `gdb ./bin core` |
| Run command per flag | `-o '<cmd>'` | `-ex '<cmd>'` |
| Run then exit | `--batch` / `-b` | `--batch` |
| Breakpoint at line | `b buggy.c:12` | `break buggy.c:12` |
| Conditional breakpoint | `br set -f f.c -l 12 -c 'i==n'` | `break f.c:12 if i==n` |
| Watchpoint | `w set var buf` | `watch buf` |
| Run / continue | `run` / `continue` | `run` / `continue` |
| Step over / into / out | `next` / `step` / `finish` | `next` / `step` / `finish` |
| Backtrace | `bt` | `bt` / `where` |
| Select frame | `frame select 1` | `frame 1` |
| Locals | `frame variable` | `info locals` / `info args` |
| Print expression | `p i + 1` | `print i + 1` |
| Memory | `x/8xw buf` | `x/8xw buf` (same syntax) |
| Registers | `register read` | `info registers` |
| Quit | `quit` | `quit` |

## When to prefer which

- **lldb** — macOS, Clang, Swift, the Foundry dev platform (the eval runs here).
- **gdb** — Linux/GCC default; richer `tui` mode; `rr` reverse-debugging integrates with it.

Both honor `-g -O0` for full locals, and both report a `SIGSEGV`/`EXC_BAD_ACCESS` at
the faulting instruction. The localization deliverable is the same: breakpoint hit,
state inspected, faulting `file:line` named.
