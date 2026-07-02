"""Materializer (design D6): deterministic writes into a consumer repo — bootstrap's
copy/fill (Wave 4) and update's migrations. `migrations/m<NNN>_<name>.py` modules each
expose `applies(repo_root) -> bool` and `apply(repo_root) -> None`.
"""
