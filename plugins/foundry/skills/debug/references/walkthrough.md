# Walkthrough — localize an out-of-bounds write

A worked [`debug`](../SKILL.md) session on the seeded bug in
`evals/fixtures/debug/buggy.c`. The program prints a wrong/garbage sum or crashes;
the task is to localize *why* with `lldb`, not by eyeballing the source.

## The program

```c
static long sum_of_squares(int n) {
    int *buf = malloc(n * sizeof(int));
    for (int i = 0; i <= n; i++) {   /* line 10 */
        buf[i] = i * i;              /* line 11 */
    }
    ...
}
```

`sum_of_squares(8)` allocates `buf` for 8 ints (`buf[0..7]`), but `i <= n` runs the
loop with `i == 8` and writes `buf[8]` — one past the buffer.

## 1. Build with debug info (and ASan to trap the write)

    cc -g -O1 -fsanitize=address evals/fixtures/debug/buggy.c -o /tmp/buggy

## 2. Break where it likely goes wrong, conditional on the bad iteration

    lldb --batch \
      -o 'br set -f buggy.c -l 11 -c '\''i == n'\''' \
      -o 'run' \
      -o 'bt' \
      -o 'frame variable' \
      -o 'quit' \
      -- /tmp/buggy

## 3. Read the stop

```
Process 12345 stopped
* thread #1, stop reason = breakpoint 1.1
    frame #0: sum_of_squares(n=8) at buggy.c:11
   10  	    for (int i = 0; i <= n; i++) {
-> 11  	        buf[i] = i * i;
(lldb) bt
  * frame #0: sum_of_squares(n=8) at buggy.c:11
    frame #1: main at buggy.c:22
(lldb) frame variable
(int) i = 8
(int) n = 8
(int *) buf = 0x0000000100... (8 ints)
```

The breakpoint **hit** at `buggy.c:11` with `i == 8` and `n == 8`. The buffer holds 8
ints (`buf[0..7]`), so `buf[8]` is one past the end.

(Without the condition, run plainly and let ASan stop the program: it reports
`heap-buffer-overflow ... WRITE of size 4` at `buggy.c:11` with the same frame.)

## 4. Localize — the deliverable

> The fault is a heap **out-of-bounds write** at `buf[i] = i * i` (`buggy.c:11`), root
> cause the loop bound `i <= n` on line 10: at the final iteration `i == n == 8`, so it
> writes `buf[8]` past the 8-element buffer. Fix: `i < n`.

That is the evidence a real session leaves — **breakpoint hit + state inspected
(`i == 8`, `n == 8`) + faulting `file:line` named** — versus a static guess, which
the eval grader rejects even when the guessed line is right.
