# pm_qms_capa

CAPA root-cause analysis supports four controlled methodologies: fixed five-slot
5 Why, multi-cause Fishbone, fixed four-dimension Is / Is Not, and a documented
Other method. The selected method is chosen in draft and locks when analysis
starts. Method-specific records are protected by the ORM after implementation
begins, while all methods share a summary and verified root cause.

The fixed structures are initialized idempotently by the Analyze workflow. The
Demo seed uses `(capa_id, sequence)` as the 5 Why identity; historical duplicate
rows remain readable and are not automatically deleted by the product.
