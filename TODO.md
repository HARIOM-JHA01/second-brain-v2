# TODO

1. Add a first-class Knowledge Base inventory tool/function that returns:
   - total file count
   - latest upload timestamp
   - optional file list with pagination
2. Replace binary intent classification (`upload` vs `other`) with multi-intent routing:
   - `upload_request`
   - `kb_inventory_query`
   - `general_question`
   - `rename_or_update_flow`
3. Add integration tests for full Twilio webhook conversation flows:
   - upload intent -> media upload -> count question
   - stale pending state expiration
   - multilingual phrasing for upload and inventory requests
4. Unify duplicated logic in `process_incoming_messages` and `process_incoming_messages_functional` into shared helpers to avoid drift.
5. Add structured logs for state transitions:
   - `file_upload_pending` set/cleared/expired
   - intent classifier output
   - final route selected
6. Improve document-grounded QA quality:
   - add explicit "summarize this uploaded document" intent handling
   - use `last_uploaded_file:{phone}` fallback when user says "this document"
   - add filename-aware retrieval when user names a document in query
7. Consolidate retrieval stack:
   - use one Pinecone search path and one metadata schema
   - remove legacy retrieval formats (`texto`/`nombre`) where not used
8. Add retrieval evaluation tests:
   - upload doc -> ask "what is this document about?" should return grounded summary
   - upload doc -> ask with filename mention should prioritize that file
