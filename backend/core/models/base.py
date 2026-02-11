# -----------------------------------------------------------------------------
# CONSTANTS CONTRACT (DSA v1.0)
# -----------------------------------------------------------------------------
EMBED_DIM = 1152  # SigLIP SO400M patch14-384
EMBED_NORMALIZE = True

# Require pgvector for VectorField support. Fail fast if missing.
try:
    from pgvector.django import VectorField
except Exception as e:
    raise RuntimeError(
        "pgvector.django.VectorField is required. Install 'pgvector' and enable the 'vector' extension in Postgres. "
        f"Original error: {e}"
    )
