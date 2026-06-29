#include <stdio.h>
#include <stdlib.h>

/* sum_of_squares(n): sum of squares 0..n-1.
 * Seeded defect: the loop uses `i <= n`, so the final iteration writes
 * buf[n] — one past the n-element buffer — a heap out-of-bounds write. */
static long sum_of_squares(int n)
{
    int *buf = malloc(n * sizeof(int));
    for (int i = 0; i <= n; i++) {   /* line 10: BUG — <= writes buf[n] */
        buf[i] = i * i;              /* line 11: the out-of-bounds write */
    }
    long total = 0;
    for (int i = 0; i < n; i++) {
        total += buf[i];
    }
    free(buf);
    return total;
}

int main(void)
{
    printf("sum=%ld\n", sum_of_squares(8));
    return 0;
}
