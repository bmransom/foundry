# Tasks — order sync

- [ ] T1: Serialize and POST an Order in `src/sync.py`; store the tracking id and
  emit the Wide event. Test in `tests/test_sync.py`. [AC-1.1, AC-1.2]
- [ ] T2: Add the retry policy in `src/retry.py` — exponential backoff for 5xx, no
  retry for 4xx. Test in `tests/test_retry.py`. [AC-2.1, AC-2.2]
- [ ] T3: Add the cache-purge CLI in `src/cli.py`. Test in `tests/test_cli.py`.
  [AC-3.1]
