"""Prepare RAG corpora and upload seed data for baseLawAgent.

Creates three Vertex AI RAG corpora (knowledge, drafting, research), optionally
uploads PDF seed documents, and writes the corpus resource names back to the
project .env file.

Usage:
    python -m baseLawAgent.shared_libraries.prepare_corpus_and_data
"""

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import requests
import vertexai
from dotenv import load_dotenv, set_key
from vertexai.preview import rag

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


@dataclass
class CorpusConfig:
    """Configuration for a single RAG corpus."""

    display_name: str
    description: str
    env_var: str
    seed_urls: list[str] = field(default_factory=list)


CORPORA: list[CorpusConfig] = [
    CorpusConfig(
        display_name="baseLawAgent-knowledge",
        description="Firm knowledge base: past work product, precedents, clause libraries, internal memos.",
        env_var="KNOWLEDGE_RAG_CORPUS",
    ),
    CorpusConfig(
        display_name="baseLawAgent-drafting",
        description="Drafting template library: standard clauses, contract templates, document formats.",
        env_var="DRAFTING_RAG_CORPUS",
    ),
    CorpusConfig(
        display_name="baseLawAgent-research",
        description="Research corpus: prior research memos, case analyses, legal briefs.",
        env_var="RESEARCH_RAG_CORPUS",
    ),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def initialize_vertex_ai() -> None:
    """Initialize the Vertex AI SDK using environment variables."""
    load_dotenv(ENV_FILE)
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    if not project:
        try:
            import google.auth

            _, project = google.auth.default()
        except Exception:
            pass
    if not project:
        raise RuntimeError(
            "GOOGLE_CLOUD_PROJECT must be set in the environment or "
            "derivable from default credentials."
        )
    vertexai.init(project=project, location=location)
    print(f"Vertex AI initialized — project={project}, location={location}")


def create_or_get_corpus(config: CorpusConfig) -> str:
    """Return the resource name of a corpus, creating it if necessary.

    If the env var already contains a valid resource name that still exists,
    that corpus is reused.  Otherwise a new corpus is created.
    """
    existing = os.environ.get(config.env_var, "").strip()
    if existing:
        try:
            corpus = rag.get_corpus(name=existing)
            print(f"  Reusing existing corpus: {corpus.name}")
            return corpus.name
        except Exception:
            print(f"  Stored corpus {existing!r} not found — creating new one.")

    corpus = rag.create_corpus(
        display_name=config.display_name,
        description=config.description,
    )
    print(f"  Created corpus: {corpus.name}")
    return corpus.name


def download_pdf_from_url(url: str, dest_dir: str) -> str:
    """Download a PDF from *url* into *dest_dir* and return the local path."""
    filename = url.rsplit("/", 1)[-1]
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    local_path = os.path.join(dest_dir, filename)
    print(f"  Downloading {url} ...")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    with open(local_path, "wb") as fh:
        fh.write(resp.content)
    print(f"  Saved to {local_path} ({len(resp.content)} bytes)")
    return local_path


def upload_pdf_to_corpus(corpus_name: str, pdf_path: str) -> None:
    """Upload a local PDF file into the given RAG corpus."""
    print(f"  Uploading {pdf_path} to {corpus_name} ...")
    rag.upload_file(
        corpus_name=corpus_name,
        path=pdf_path,
        display_name=os.path.basename(pdf_path),
    )
    print("  Upload complete.")


def update_env_file(env_var: str, value: str) -> None:
    """Write or update a key in the project .env file."""
    set_key(str(ENV_FILE), env_var, value)
    os.environ[env_var] = value
    print(f"  {env_var} written to {ENV_FILE}")


def list_corpus_files(corpus_name: str) -> None:
    """Print the files currently stored in a corpus."""
    files = rag.list_files(corpus_name=corpus_name)
    file_list = list(files)
    if not file_list:
        print("  (no files)")
        return
    for f in file_list:
        print(f"  - {f.display_name}  ({f.name})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Create / verify all corpora and optionally upload seed PDFs."""
    initialize_vertex_ai()

    for config in CORPORA:
        print(f"\n=== {config.display_name} ({config.env_var}) ===")
        corpus_name = create_or_get_corpus(config)
        update_env_file(config.env_var, corpus_name)

        # Upload seed PDFs if configured
        if config.seed_urls:
            with tempfile.TemporaryDirectory() as tmpdir:
                for url in config.seed_urls:
                    pdf_path = download_pdf_from_url(url, tmpdir)
                    upload_pdf_to_corpus(corpus_name, pdf_path)

        print("  Current files:")
        list_corpus_files(corpus_name)

    print("\nAll corpora ready.")


if __name__ == "__main__":
    main()
