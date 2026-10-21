import os
import re
import sys
import json
import uuid
import shutil
import zipfile
import difflib
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple


# Maximum limits for security against zip-bombs and oversized uploads
MAX_ZIP_SIZE_BYTES = 25 * 1024 * 1024       # 25 MB
MAX_EXTRACTED_FILES = 1000
MAX_UNCOMPRESSED_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB
IGNORED_WORKSPACE_DIRS = {".git", "__pycache__", "venv", ".venv", "node_modules", ".pytest_cache", ".next", "dist", "build"}


class WorkspaceSecurityError(Exception):
    """Raised when an uploaded zip violates security policies or attempts path traversal."""
    pass


class WorkspaceManager:
    """
    Manages isolated project workspaces for uploaded repositories.
    Guarantees:
      - Safe extraction preventing Zip-Slip / path traversal
      - Preservation of untouched original snapshot
      - Safe relative path resolution within the isolated working directory
      - Diff generation between original and current files
      - Reset capability
    """

    def __init__(self, base_workspaces_dir: Optional[str] = None):
        if base_workspaces_dir:
            self.base_dir = Path(base_workspaces_dir).resolve()
        else:
            # Default to backend/workspaces
            self.base_dir = Path(__file__).resolve().parent.parent.parent.parent / "workspaces"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def get_project_dir(self, project_id: str) -> Path:
        return self.base_dir / project_id

    def get_src_dir(self, project_id: str) -> Path:
        return self.get_project_dir(project_id) / "src"

    def get_original_dir(self, project_id: str) -> Path:
        return self.get_project_dir(project_id) / "original"

    def resolve_safe_path(self, project_id: str, relative_path: str) -> Path:
        """
        Resolves a relative path inside the project's src directory.
        Raises WorkspaceSecurityError if the path escapes the src boundary.
        """
        src_dir = self.get_src_dir(project_id).resolve()
        if not src_dir.exists():
            raise FileNotFoundError(f"Project '{project_id}' src directory not found.")

        # Clean normalized path
        norm_path = os.path.normpath(relative_path.strip().lstrip("/\\"))
        resolved = (src_dir / norm_path).resolve()

        try:
            # Check if resolved path is strictly inside src_dir
            resolved.relative_to(src_dir)
        except ValueError:
            raise WorkspaceSecurityError(f"Path traversal detected: '{relative_path}' escapes workspace.")

        return resolved

    def create_project_from_zip(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Safely validates and extracts a zip archive into an isolated project workspace.
        """
        if len(file_bytes) > MAX_ZIP_SIZE_BYTES:
            raise WorkspaceSecurityError(
                f"Uploaded archive size ({len(file_bytes)} bytes) exceeds max limit of {MAX_ZIP_SIZE_BYTES} bytes."
            )

        project_id = f"proj-{uuid.uuid4().hex[:10]}"
        project_dir = self.get_project_dir(project_id)
        src_dir = self.get_src_dir(project_id)
        original_dir = self.get_original_dir(project_id)

        project_dir.mkdir(parents=True, exist_ok=True)
        src_dir.mkdir(parents=True, exist_ok=True)
        original_dir.mkdir(parents=True, exist_ok=True)

        # Save raw zip archive
        zip_path = project_dir / "archive.zip"
        zip_path.write_bytes(file_bytes)

        total_extracted_size = 0
        file_count = 0
        extracted_files: List[str] = []

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                infolist = zf.infolist()
                if len(infolist) > MAX_EXTRACTED_FILES:
                    raise WorkspaceSecurityError(
                        f"Zip contains {len(infolist)} files, exceeding limit of {MAX_EXTRACTED_FILES}."
                    )

                # First pass: strictly validate all entries for path traversal
                for member in infolist:
                    filename_entry = member.filename
                    if "\x00" in filename_entry:
                        raise WorkspaceSecurityError("Archive entry contains null byte.")
                    if filename_entry.startswith(("/", "\\")):
                        raise WorkspaceSecurityError(f"Absolute path in archive forbidden: '{filename_entry}'")
                    
                    parts = Path(filename_entry).parts
                    if ".." in parts:
                        raise WorkspaceSecurityError(f"Path traversal attempt detected in archive: '{filename_entry}'")

                    total_extracted_size += member.file_size
                    if total_extracted_size > MAX_UNCOMPRESSED_SIZE_BYTES:
                        raise WorkspaceSecurityError("Uncompressed archive size exceeds maximum limit (zip-bomb protection).")

                # Second pass: safe extraction into both src and original
                for member in infolist:
                    clean_name = member.filename.replace("\\", "/").strip()
                    if clean_name.endswith("/"):
                        (src_dir / clean_name).mkdir(parents=True, exist_ok=True)
                        (original_dir / clean_name).mkdir(parents=True, exist_ok=True)
                        continue

                    target_src = (src_dir / clean_name).resolve()
                    target_orig = (original_dir / clean_name).resolve()

                    target_src.relative_to(src_dir)
                    target_orig.relative_to(original_dir)

                    target_src.parent.mkdir(parents=True, exist_ok=True)
                    target_orig.parent.mkdir(parents=True, exist_ok=True)

                    with zf.open(member) as source_file:
                        content = source_file.read()
                        target_src.write_bytes(content)
                        target_orig.write_bytes(content)

                    file_count += 1
                    extracted_files.append(clean_name)

        except Exception as e:
            shutil.rmtree(project_dir, ignore_errors=True)
            if isinstance(e, WorkspaceSecurityError):
                raise
            raise WorkspaceSecurityError(f"Failed to extract zip archive safely: {str(e)}")

        project_name = Path(filename).stem
        metadata = {
            "project_id": project_id,
            "name": project_name,
            "filename": filename,
            "file_count": file_count,
            "total_size_bytes": len(file_bytes),
            "uncompressed_size_bytes": total_extracted_size,
            "created_at": self._now(),
            "files": sorted(extracted_files),
        }

        (project_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return metadata

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        meta_file = self.get_project_dir(project_id) / "metadata.json"
        if not meta_file.exists():
            return None
        try:
            return json.loads(meta_file.read_text(encoding="utf-8"))
        except Exception:
            return None

    def list_projects(self) -> List[Dict[str, Any]]:
        projects = []
        if not self.base_dir.exists():
            return projects
        for d in self.base_dir.iterdir():
            if d.is_dir() and (d / "metadata.json").exists():
                proj = self.get_project(d.name)
                if proj:
                    projects.append(proj)
        return sorted(projects, key=lambda x: x.get("created_at", ""), reverse=True)

    def reset_project(self, project_id: str) -> Dict[str, Any]:
        """
        Resets the src working copy to the untouched original snapshot safely on Windows.
        """
        src_dir = self.get_src_dir(project_id)
        orig_dir = self.get_original_dir(project_id)

        if not orig_dir.exists():
            raise FileNotFoundError(f"Original snapshot for project '{project_id}' does not exist.")

        # Re-copy all original files over to src_dir
        for orig_file in orig_dir.rglob("*"):
            if orig_file.is_file():
                rel = orig_file.relative_to(orig_dir)
                dest = src_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(orig_file, dest)

        # Remove any modified/extra files that don't exist in original
        for src_file in list(src_dir.rglob("*")):
            if src_file.is_file():
                rel = src_file.relative_to(src_dir)
                if not (orig_dir / rel).exists() and not any(part in IGNORED_WORKSPACE_DIRS for part in src_file.parts):
                    try:
                        src_file.unlink()
                    except Exception:
                        pass

        return {
            "status": "success",
            "project_id": project_id,
            "message": "Project workspace reset to original uploaded snapshot."
        }

    def get_workspace_diff(self, project_id: str) -> Dict[str, Any]:
        """
        Calculates unified diff between original and current src files, ignoring caches and artifacts.
        """
        src_dir = self.get_src_dir(project_id)
        orig_dir = self.get_original_dir(project_id)

        if not src_dir.exists() or not orig_dir.exists():
            return {"changed_files": [], "diff": "", "total_changed_files": 0}

        def is_ignored(p: Path) -> bool:
            return any(part in IGNORED_WORKSPACE_DIRS or part.endswith(".pyc") for part in p.parts)

        src_files = {
            p.relative_to(src_dir).as_posix()
            for p in src_dir.rglob("*")
            if p.is_file() and not is_ignored(p)
        }
        orig_files = {
            p.relative_to(orig_dir).as_posix()
            for p in orig_dir.rglob("*")
            if p.is_file() and not is_ignored(p)
        }

        all_paths = sorted(src_files | orig_files)
        changed_files = []
        all_diff_lines = []

        for rel_path in all_paths:
            src_file = src_dir / rel_path
            orig_file = orig_dir / rel_path

            src_content = ""
            orig_content = ""

            if orig_file.exists():
                try:
                    orig_content = orig_file.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue

            if src_file.exists():
                try:
                    src_content = src_file.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue

            if src_content != orig_content:
                changed_files.append(rel_path)
                diff = difflib.unified_diff(
                    orig_content.splitlines(keepends=True),
                    src_content.splitlines(keepends=True),
                    fromfile=f"a/{rel_path}",
                    tofile=f"b/{rel_path}"
                )
                all_diff_lines.extend(diff)

        full_diff = "".join(all_diff_lines)
        return {
            "project_id": project_id,
            "changed_files": changed_files,
            "total_changed_files": len(changed_files),
            "diff": full_diff
        }

    def create_sample_broken_project(self) -> Dict[str, Any]:
        """
        Creates a built-in sample defective project with a real bug and real pytest tests.
        Bug: customer_service.py returns {"email": customer.email} but invoice_worker.py expects customer["customer_email"].
        Test: test_invoice_worker.py executes and fails with KeyError: 'customer_email'.
        """
        project_id = "sample-broken-invoice-project"
        project_dir = self.get_project_dir(project_id)
        src_dir = self.get_src_dir(project_id)
        original_dir = self.get_original_dir(project_id)

        # Clear if already exists
        shutil.rmtree(project_dir, ignore_errors=True)
        project_dir.mkdir(parents=True, exist_ok=True)
        src_dir.mkdir(parents=True, exist_ok=True)
        original_dir.mkdir(parents=True, exist_ok=True)

        files = {
            "customer_service.py": (
                "# Customer Profile API Service\n"
                "class CustomerService:\n"
                "    def __init__(self):\n"
                "        self.db = {\n"
                "            'CUST-001': {'name': 'Acme Corp', 'email': 'billing@acme.test', 'plan': 'enterprise'},\n"
                "            'CUST-002': {'name': 'Globex Inc', 'email': 'finance@globex.test', 'plan': 'pro'}\n"
                "        }\n"
                "\n"
                "    def get_customer_profile(self, customer_id: str) -> dict:\n"
                "        if customer_id not in self.db:\n"
                "            raise ValueError(f'Customer {customer_id} not found')\n"
                "        c = self.db[customer_id]\n"
                "        # Recent change: field renamed from customer_email to email\n"
                "        return {\n"
                "            'customer_id': customer_id,\n"
                "            'customer_name': c['name'],\n"
                "            'email': c['email'],\n"
                "            'plan': c['plan']\n"
                "        }\n"
            ),
            "invoice_worker.py": (
                "# Invoice Generation and Dispatch Worker\n"
                "from customer_service import CustomerService\n"
                "\n"
                "def process_invoice(customer_id: str, amount_cents: int) -> dict:\n"
                "    svc = CustomerService()\n"
                "    profile = svc.get_customer_profile(customer_id)\n"
                "    \n"
                "    # Dependent workflow expects 'customer_email' or 'email'\n"
                "    recipient_email = profile['customer_email']\n"
                "    \n"
                "    return {\n"
                "        'status': 'DISPATCHED',\n"
                "        'customer_id': customer_id,\n"
                "        'recipient': recipient_email,\n"
                "        'amount_cents': amount_cents,\n"
                "        'invoice_id': f'INV-{customer_id}-99'\n"
                "    }\n"
            ),
            "test_invoice_worker.py": (
                "# Test suite verifying invoice dispatch workflow\n"
                "import pytest\n"
                "from invoice_worker import process_invoice\n"
                "\n"
                "def test_process_invoice_success():\n"
                "    result = process_invoice('CUST-001', 5000)\n"
                "    assert result['status'] == 'DISPATCHED'\n"
                "    assert result['recipient'] == 'billing@acme.test'\n"
                "    assert result['amount_cents'] == 5000\n"
                "\n"
                "def test_process_invoice_second_customer():\n"
                "    result = process_invoice('CUST-002', 12500)\n"
                "    assert result['status'] == 'DISPATCHED'\n"
                "    assert result['recipient'] == 'finance@globex.test'\n"
            ),
            "requirements.txt": "pytest>=8.0.0\n",
            "README.md": (
                "# Invoice Generation Service\n\n"
                "A microservice processing customer invoices and dispatching notifications.\n"
                "Run tests using `pytest`.\n"
            )
        }

        extracted_files = []
        for rel_path, content in files.items():
            s_file = src_dir / rel_path
            o_file = original_dir / rel_path
            s_file.parent.mkdir(parents=True, exist_ok=True)
            o_file.parent.mkdir(parents=True, exist_ok=True)
            s_file.write_text(content, encoding="utf-8")
            o_file.write_text(content, encoding="utf-8")
            extracted_files.append(rel_path)

        metadata = {
            "project_id": project_id,
            "name": "Invoice Billing Service (Sample Broken Project)",
            "filename": "sample_invoice_project.zip",
            "file_count": len(files),
            "total_size_bytes": sum(len(c) for c in files.values()),
            "uncompressed_size_bytes": sum(len(c) for c in files.values()),
            "created_at": self._now(),
            "files": sorted(extracted_files),
            "is_sample": True
        }

        (project_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return metadata


workspace_manager = WorkspaceManager()
