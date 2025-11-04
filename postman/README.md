Postman collection for the `fastapi-base` project
===============================================

Files
-----

- `fastapi-base.postman_collection.json` — Postman v2.1 collection containing example requests for the running app (GET `/`, POST `/items`, GET `/items/{id}`).

How to use
----------

1. Start the app locally (example):

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

2. Import the collection in Postman:

- In Postman choose "Import" → File and select `postman/fastapi-base.postman_collection.json`.

3. Configure the `base_url` collection variable (defaults to `http://localhost:8000`):

- In Postman, edit the collection's variables and confirm `base_url` is `http://localhost:8000` (or change to your host/port).

4. Try the requests:

- `Root - GET /` — sanity check endpoint.
- `Create Item - POST /items` — create a new item (JSON body provided in the request). Use a unique `id` per item.
- `Get Item - GET /items/:id` — fetch an item by id.

Notes
-----

- The collection is intentionally minimal. If you want, I can add example test scripts, pre-request scripts to set variables, or an environment file with different base_url entries (local / CI / staging).
