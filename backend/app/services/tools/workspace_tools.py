import os
import re
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from backend.app.services.workspace.workspace_manager import workspace_manager, WorkspaceSecurityError


IGNORED_DIRECTORIES = {".git", "__pycache__", "venv", ".venv", "node_modules", ".pytest_cache", ".next", "dist", "build"}


def list_project_files(project_id: str, subpath: str = ".", **kwargs) -> Dict[str, Any]:
    """
    List files and directories in the project workspace.
    Returns relative file paths, sizes, and directory structures.
    """
    try:
        target_dir = workspace_manager.resolve_safe_path(project_id, subpath)
        if not target_dir.is_dir():
            return {"status": "error", "error": f"Path '{subpath}' is not a directory."}

        src_dir = workspace_manager.get_src_dir(project_id)
        entries = []
        for root, dirs, files in os.walk(target_dir):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRECTORIES]
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(src_dir).as_posix()
                try:
                    size = full_path.stat().st_size
                except Exception:
                    size = 0
                entries.append({
                    "path": rel_path,
                    "filename": file,
                    "size_bytes": size,
                    "extension": full_path.suffix.lower()
                })

        return {
            "status": "success",
            "project_id": project_id,
            "subpath": subpath,
            "total_files": len(entries),
            "files": entries[:300]
        }
    except Exception as e:
        return {"status": "error", "error": f"Failed to list files: {str(e)}"}


def search_code(project_id: str, query: str, file_pattern: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Search source code across project files for a query string or regex pattern.
    Returns matching file paths, line numbers, and matching text lines.
    """
    if not query or not isinstance(query, str):
        return {"status": "error", "error": "Query string must be a non-empty string."}

    try:
        src_dir = workspace_manager.get_src_dir(project_id)
        if not src_dir.exists():
            return {"status": "error", "error": f"Project '{project_id}' workspace not found."}

        pattern = None
        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error:
            # Fall back to literal search if regex is invalid
            pattern = re.compile(re.escape(query), re.IGNORECASE)

        matches = []
        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRECTORIES]
            for file in files:
                if file_pattern and not re.search(file_pattern, file):
                    continue

                full_path = Path(root) / file
                rel_path = full_path.relative_to(src_dir).as_posix()

                # Skip binary or very large files (>1MB)
                try:
                    if full_path.stat().st_size > 1024 * 1024:
                        continue
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            if pattern.search(line):
                                matches.append({
                                    "file": rel_path,
                                    "line": line_num,
                                    "text": line.strip()
                                })
                                if len(matches) >= 100:
                                    break
                except Exception:
                    continue

            if len(matches) >= 100:
                break

        return {
            "status": "success",
            "project_id": project_id,
            "query": query,
            "total_matches": len(matches),
            "matches": matches
        }
    except Exception as e:
        return {"status": "error", "error": f"Search failed: {str(e)}"}


def read_file(project_id: str, file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None, **kwargs) -> Dict[str, Any]:
    """
    Read the contents of a specific file in the project workspace with optional line ranges.
    """
    if not file_path:
        return {"status": "error", "error": "file_path is required."}

    try:
        safe_path = workspace_manager.resolve_safe_path(project_id, file_path)
        if not safe_path.is_file():
            return {"status": "error", "error": f"File '{file_path}' does not exist or is a directory."}

        content = safe_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        total_lines = len(lines)

        s_line = max(1, start_line) if start_line is not None else 1
        e_line = min(total_lines, end_line) if end_line is not None else total_lines

        selected_lines = lines[s_line - 1 : e_line]
        numbered_content = "\n".join(f"{i + s_line}: {line}" for i, line in enumerate(selected_lines))

        return {
            "status": "success",
            "project_id": project_id,
            "file_path": file_path,
            "total_lines": total_lines,
            "start_line": s_line,
            "end_line": e_line,
            "content": numbered_content,
            "raw_content": "\n".join(selected_lines)
        }
    except WorkspaceSecurityError as sec_err:
        return {"status": "error", "error": str(sec_err)}
    except Exception as e:
        return {"status": "error", "error": f"Failed to read file '{file_path}': {str(e)}"}


def inspect_dependencies(project_id: str, **kwargs) -> Dict[str, Any]:
    """
    Inspect project dependency manifests (e.g. package.json, requirements.txt, pyproject.toml).
    Returns discovered dependencies, scripts, and runtime configurations.
    """
    try:
        src_dir = workspace_manager.get_src_dir(project_id)
        discovered = {}

        # 1. requirements.txt
        req_file = src_dir / "requirements.txt"
        if req_file.exists():
            discovered["requirements.txt"] = [
                line.strip() for line in req_file.read_text(encoding="utf-8", errors="ignore").splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]

        # 2. pyproject.toml
        pyproj_file = src_dir / "pyproject.toml"
        if pyproj_file.exists():
            discovered["pyproject.toml"] = pyproj_file.read_text(encoding="utf-8", errors="ignore")[:2000]

        # 3. package.json
        pkg_file = src_dir / "package.json"
        if pkg_file.exists():
            try:
                import json
                pkg_data = json.loads(pkg_file.read_text(encoding="utf-8", errors="ignore"))
                discovered["package.json"] = {
                    "dependencies": pkg_data.get("dependencies", {}),
                    "devDependencies": pkg_data.get("devDependencies", {}),
                    "scripts": pkg_data.get("scripts", {})
                }
            except Exception:
                discovered["package.json"] = "Could not parse JSON"

        return {
            "status": "success",
            "project_id": project_id,
            "manifests_found": list(discovered.keys()),
            "dependencies": discovered
        }
    except Exception as e:
        return {"status": "error", "error": f"Dependency inspection failed: {str(e)}"}


def discover_tests_and_commands(project_id: str, **kwargs) -> Dict[str, Any]:
    """
    Discover existing test files, test frameworks, and test runner execution commands.
    """
    try:
        src_dir = workspace_manager.get_src_dir(project_id)
        test_files = []
        framework = "unknown"
        suggested_command = None

        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRECTORIES]
            for file in files:
                rel = (Path(root) / file).relative_to(src_dir).as_posix()
                if (
                    file.startswith("test_")
                    or file.endswith("_test.py")
                    or "tests/" in rel
                    or file.endswith(".test.js")
                    or file.endswith(".spec.js")
                ):
                    test_files.append(rel)

        if any(f.endswith(".py") for f in test_files):
            framework = "pytest"
            suggested_command = "pytest"
        elif any(f.endswith(".js") or f.endswith(".ts") for f in test_files):
            framework = "npm test"
            suggested_command = "npm test"

        return {
            "status": "success",
            "project_id": project_id,
            "test_framework": framework,
            "suggested_command": suggested_command,
            "total_test_files": len(test_files),
            "test_files": test_files
        }
    except Exception as e:
        return {"status": "error", "error": f"Test discovery failed: {str(e)}"}


def run_tests(project_id: str, test_command: Optional[str] = None, test_path: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Execute tests inside the project workspace using a secure subprocess environment.
    Returns actual command output, execution time, pass/fail status, and exit code.
    """
    try:
        src_dir = workspace_manager.get_src_dir(project_id)
        if not src_dir.exists():
            return {"status": "error", "error": f"Project workspace '{project_id}' does not exist."}

        # Determine executable command
        # Security: only allow safe test runners
        cmd = []
        custom_cmd = test_command.strip() if test_command else ""

        if not custom_cmd or custom_cmd.startswith("pytest"):
            cmd = [sys.executable, "-m", "pytest", "-v"]
            if test_path:
                safe_target = workspace_manager.resolve_safe_path(project_id, test_path)
                cmd.append(safe_target.relative_to(src_dir).as_posix())
        elif custom_cmd.startswith("unittest") or "unittest" in custom_cmd:
            cmd = [sys.executable, "-m", "unittest", "discover", "-v"]
        elif custom_cmd.startswith("npm test"):
            cmd = ["npm", "test"]
        else:
            # Fall back to pytest
            cmd = [sys.executable, "-m", "pytest", "-v"]

        start_t = time.time()
        # Set environment with PYTHONPATH pointing to src_dir so project modules resolve
        env = os.environ.copy()
        env["PYTHONPATH"] = str(src_dir)
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        proc = subprocess.run(
            cmd,
            cwd=str(src_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=25
        )
        duration = round(time.time() - start_t, 3)

        passed = (proc.returncode == 0)
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        combined_output = (stdout + ("\n--- STDERR ---\n" + stderr if stderr else "")).strip()

        # Parse summary counts if pytest
        tests_passed = None
        tests_failed = None
        if "passed" in stdout or "failed" in stdout:
            p_match = re.search(r"(\d+)\s+passed", stdout)
            f_match = re.search(r"(\d+)\s+failed", stdout)
            if p_match:
                tests_passed = int(p_match.group(1))
            if f_match:
                tests_failed = int(f_match.group(1))

        return {
            "status": "success",
            "project_id": project_id,
            "command": " ".join([Path(cmd[0]).name] + cmd[1:]),
            "exit_code": proc.returncode,
            "passed": passed,
            "duration_seconds": duration,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "output": combined_output,
            "message": "Tests passed successfully." if passed else "Tests failed with errors."
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "project_id": project_id,
            "error": "Test execution timed out after 25 seconds.",
            "passed": False,
            "exit_code": -1
        }
    except Exception as e:
        return {"status": "error", "error": f"Failed to execute tests: {str(e)}"}


def edit_file(project_id: str, file_path: str, target: str, replacement: str, **kwargs) -> Dict[str, Any]:
    """
    Modify a source file in the isolated workspace by replacing a target code snippet.
    Guarantees the target snippet exists before replacing.
    """
    if not file_path or not target:
        return {"status": "error", "error": "file_path and target are required."}

    try:
        safe_path = workspace_manager.resolve_safe_path(project_id, file_path)
        if not safe_path.is_file():
            return {"status": "error", "error": f"File '{file_path}' does not exist."}

        content = safe_path.read_text(encoding="utf-8")
        if target not in content:
            return {
                "status": "error",
                "error": f"Target snippet not found in '{file_path}'. Verify exact whitespace and lines."
            }

        new_content = content.replace(target, replacement, 1)
        safe_path.write_text(new_content, encoding="utf-8")

        return {
            "status": "success",
            "project_id": project_id,
            "file_path": file_path,
            "message": f"Successfully applied edit to '{file_path}'."
        }
    except WorkspaceSecurityError as sec_err:
        return {"status": "error", "error": str(sec_err)}
    except Exception as e:
        return {"status": "error", "error": f"Failed to edit file '{file_path}': {str(e)}"}


def write_file(project_id: str, file_path: str, content: str, **kwargs) -> Dict[str, Any]:
    """
    Write or overwrite a file in the project workspace with the given content.
    """
    if not file_path:
        return {"status": "error", "error": "file_path is required."}

    try:
        safe_path = workspace_manager.resolve_safe_path(project_id, file_path)
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        safe_path.write_text(content, encoding="utf-8")

        return {
            "status": "success",
            "project_id": project_id,
            "file_path": file_path,
            "bytes_written": len(content),
            "message": f"Successfully wrote file '{file_path}'."
        }
    except WorkspaceSecurityError as sec_err:
        return {"status": "error", "error": str(sec_err)}
    except Exception as e:
        return {"status": "error", "error": f"Failed to write file '{file_path}': {str(e)}"}


def revert_file(project_id: str, file_path: str, **kwargs) -> Dict[str, Any]:
    """
    Revert a modified file back to its original uploaded snapshot.
    """
    if not file_path:
        return {"status": "error", "error": "file_path is required."}

    try:
        src_file = workspace_manager.resolve_safe_path(project_id, file_path)
        orig_dir = workspace_manager.get_original_dir(project_id)
        orig_file = orig_dir / file_path

        if not orig_file.exists():
            return {"status": "error", "error": f"Original file for '{file_path}' does not exist in snapshot."}

        import shutil
        shutil.copy2(orig_file, src_file)
        return {
            "status": "success",
            "project_id": project_id,
            "file_path": file_path,
            "message": f"Reverted '{file_path}' to original snapshot."
        }
    except WorkspaceSecurityError as sec_err:
        return {"status": "error", "error": str(sec_err)}
    except Exception as e:
        return {"status": "error", "error": f"Failed to revert file '{file_path}': {str(e)}"}


def get_workspace_diff(project_id: str, **kwargs) -> Dict[str, Any]:
    """
    Retrieve unified diff comparing current workspace files against original uploaded snapshot.
    """
    try:
        return {
            "status": "success",
            **workspace_manager.get_workspace_diff(project_id)
        }
    except Exception as e:
        return {"status": "error", "error": f"Failed to compute workspace diff: {str(e)}"}


# Registry of tools available for the live AI agent
WORKSPACE_TOOLS = {
    "list_project_files": list_project_files,
    "search_code": search_code,
    "read_file": read_file,
    "inspect_dependencies": inspect_dependencies,
    "discover_tests_and_commands": discover_tests_and_commands,
    "run_tests": run_tests,
    "edit_file": edit_file,
    "write_file": write_file,
    "revert_file": revert_file,
    "get_workspace_diff": get_workspace_diff,
}
