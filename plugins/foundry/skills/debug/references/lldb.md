# lldb cheatsheet

The full command set behind [`../SKILL.md`](../SKILL.md). lldb accepts both the long
form (`breakpoint set`) and the alias (`b`); aliases are shown after `=`.

## Launch, attach, core

| Goal | Command |
|---|---|
| Launch a binary | `lldb ./bin` then `run [args]`, or `lldb --batch -o run -- ./bin args` |
| Pass args / stdin | `run arg1 arg2`, `process launch -i input.txt` |
| Attach to a running process | `lldb -p <pid>` or `(lldb) process attach --pid <pid>` |
| Attach by name | `process attach --name bin --waitfor` |
| Open a core dump | `lldb -c core ./bin` (macOS cores: raise the limit with `ulimit -c unlimited`) |
| Environment / cwd | `process launch -E VAR=val -w /path` |

Build first with `cc -g -O0` (or `-Og`); `-O2` elides locals and inlines frames so
`frame variable` reads `<unavailable>`.

## Breakpoints

| Goal | Command (alias) |
|---|---|
| At a file:line | `breakpoint set -f buggy.c -l 12` = `b buggy.c:12` |
| At a function | `b main`, `b 'Namespace::method'` |
| Conditional | `br set -f buggy.c -l 12 -c 'i == n'` |
| Ignore first N hits | `br set -n f -i 3` |
| One-shot | `br set -o -n f` |
| Command on hit | `br command add <id>` then lines, `DONE` (e.g. auto-`bt; continue`) |
| List / delete / disable | `br list`, `br delete <id>`, `br disable <id>` |

## Watchpoints (catch a bad write/read)

| Goal | Command |
|---|---|
| Break when a variable changes | `watchpoint set variable buf` = `w set var buf` |
| Break on an address | `w set expression -- &buf[8]` |
| Read-only / read-write | `w set var -w read buf` |
| List / delete | `watchpoint list`, `watchpoint delete <id>` |

## Execution control

| Goal | Command (alias) |
|---|---|
| Run / continue | `run` (`r`), `continue` (`c`) |
| Step over / into / out | `next` (`n`), `step` (`s`), `finish` |
| Step one instruction | `ni`, `si` |
| Run to a line | `thread until 20` |
| Stop reason after a crash | shown automatically: `stop reason = EXC_BAD_ACCESS (...)` |

## Inspection

| Goal | Command (alias) |
|---|---|
| Backtrace | `thread backtrace` = `bt` (`bt all` for every thread) |
| Select a frame | `frame select 1` = `f 1`, `up`, `down` |
| Locals + args of the frame | `frame variable` = `fr v` (one var: `fr v buf`) |
| Evaluate an expression | `p i + 1`, `expression -- buf[8] = 0` (side effects allowed) |
| Print as type/format | `p/x addr`, `parray 8 buf` (array), `p *ptr` |
| Memory | `memory read -c 8 -f x -s 4 buf` = `x/8xw buf` |
| Registers | `register read`, `register read rdi` |
| Source around the stop | `source list`, `f` (shows the line) |
| Threads | `thread list`, `thread select 2` |

## Common stop reasons

- `EXC_BAD_ACCESS` / `SIGSEGV` — bad pointer (null, freed, out of bounds). `bt` +
  `frame variable` at the faulting frame names the deref.
- `SIGABRT` — an assert, `abort()`, or a libc/ASan fault (a heap message often precedes it).
- `breakpoint N.N` — a breakpoint you set was hit (the evidence a real session leaves).
- `watchpoint N` — a watched location changed; the previous/new value is printed.

## Tips

- ASan amplifies memory bugs: `cc -g -O1 -fno-inline -fsanitize=address` makes an
  out-of-bounds write trap *at the write*, not later (`-fno-inline` keeps the faulting
  line out of an inlined caller's frame).
- `settings set target.process.stop-on-exec false` to run past `exec`.
- Script a whole session into a file and run `lldb -s session.lldb -- ./bin`.
