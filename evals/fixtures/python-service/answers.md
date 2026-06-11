# Canned interview answers — python-service fixture

1. **Project description:** catalog is a product-catalog HTTP service: a
   FastAPI app serving Product records as JSON over `GET /products/{sku}`.
   Consumed by storefront clients; one served entrypoint
   (`uvicorn catalog.main:app`).
2. **Domain terms (canonical — wrong name now debt):**
   - Product — the sellable record; wrong name: Merchandise
   - Catalog — the grouping a Product belongs to; wrong name: Assortment
   - SKU — the canonical Product identifier; wrong name: ArticleCode
   - Listing — a Product exposed through the API; wrong name: Posting
   - Merchant — the party that owns Products; wrong name: Seller
3. **Vocabulary polarity:** embrace — it is a product; use domain terms freely.
4. **API surface:** yes — an HTTP JSON API (FastAPI + pydantic models).
5. **Gate commands:** `ruff check .` and `pytest -q` (the configured tools).
6. **Parallel agents:** no — solo development on this machine.
7. **Unit of work:** one request — one wide event per handled HTTP request.
8. **First epic:** Epic 0 — Serve the catalog (products resolve by SKU through
   the gated service).
