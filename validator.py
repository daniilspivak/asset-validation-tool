
from pathlib import Path

def build_reference_snapshot(reference_folder_path):    # creating reference folder
    messages = []
    ref_root = Path(reference_folder_path)

    if not ref_root.exists():   #checks if the folder exists and it is a folder
        messages.append(f"[ERROR] Reference folder does not exist: {ref_root}")
        return None, messages
    if not ref_root.is_dir():
        messages.append(f"[ERROR] [ERROR] Reference path is not a folder: {ref_root}")
        return None, messages

    ref_folders = set()
    ref_files = set()

    for p in ref_root.rglob("*"):
        rel = p.relative_to(ref_root).as_posix()

        if p.is_dir():
            ref_folders.add(rel)
        elif p.is_file():
            ref_files.add(rel)

    messages.append(f"[OK] Reference snapshot collected. Folders: {len(ref_folders)} | Files: {len(ref_files)}")
    snapshot = {
        "root": str(ref_root),
        "folders": sorted(ref_folders),
        "files": sorted(ref_files),
    }

    return snapshot, messages


def _norm(p: str) -> str:
    return p.replace("\\", "/").lower()

def _is_under_ignored_dir(rel_path: str, ignore_dirs: list[str]) -> bool:
    p = _norm(rel_path)
    for d in ignore_dirs or []:
        dd = _norm(d).strip("/")
        if not dd:
            continue
        if p == dd or p.startswith(dd + "/"):
            return True
    return False

def _extract_suffix_from_ref_stem(ref_stem: str) -> str:
    if "_" in ref_stem:
        return "_" + ref_stem.split("_", 1)[1]
    return ""

def validate_asset(asset_name, asset_folder_path, ref_snapshot, ignore_dirs=None):
    if ignore_dirs is None:
        ignore_dirs = []

    messages = []
    asset_folder = Path(asset_folder_path)

    if not asset_folder.exists():   #checks if the folder exists and it is a folder
        messages.append(f"[ERROR] Path does not exist: {asset_folder}")
        return False, messages
    if not asset_folder.is_dir():
        messages.append(f"[ERROR] Path exists but is NOT a folder: {asset_folder}")
        return False, messages

    folder_name = asset_folder.name   #checks if asset name matches folder name
    if folder_name != asset_name:
        messages.append(f"[ERROR] Folder name '{folder_name}' does not match asset name '{asset_name}'")
        return False, messages

    asset_folders = set()
    asset_files = set()

    for p in asset_folder.rglob("*"):
        rel = p.relative_to(asset_folder).as_posix()
        if p.is_dir():
            asset_folders.add(rel)
        elif p.is_file():
            asset_files.add(rel)

    ref_folders_all = set(ref_snapshot["folders"])
    ref_folders = {f for f in ref_folders_all if not _is_under_ignored_dir(f, ignore_dirs)}

    asset_folders_filtered = {f for f in asset_folders if not _is_under_ignored_dir(f, ignore_dirs)}

    missing = sorted(ref_folders - asset_folders_filtered)
    extra_folders = sorted(asset_folders_filtered - ref_folders)

    is_ok = True
    for f in missing:
        messages.append(f"[ERROR] Missing folder: {f}")
        is_ok = False

    for f in extra_folders:
        messages.append(f"[WARN] Extra folder: {f}")


    #check files(not folders)

    ref_files_all = [Path(x) for x in ref_snapshot["files"]]
    ref_files = [rf for rf in ref_files_all if not _is_under_ignored_dir(rf.as_posix(), ignore_dirs)]
    index = {}
    for f in asset_files:
        fp = Path(f)
        key = (_norm(fp.parent.as_posix()), fp.suffix.lower())
        index.setdefault(key, []).append(fp.name)

    asset_files_norm = {_norm(x) for x in asset_files}

    expected_files = []

    for rf in ref_files:
        rel_dir = rf.parent
        ext = rf.suffix.lower()
        suffix = _extract_suffix_from_ref_stem(rf.stem)

        expected_name = f"{asset_name}{suffix}{ext}"
        expected = (rel_dir / expected_name).as_posix()
        expected_files.append(expected)

        if _norm(expected) not in asset_files_norm:
            key = (_norm(rel_dir.as_posix()), ext)
            candidates = index.get(key, [])

            if candidates:
                messages.append(
                    f"[ERROR] Wrong naming in '{rel_dir.as_posix()}': expected '{expected_name}', "
                    f"found: {', '.join(candidates)}"
                )
            else:
                messages.append(f"[ERROR] Missing file: {expected}")
            is_ok = False

    expected_norm = {_norm(x) for x in expected_files}
    extra_files = sorted(
        f for f in asset_files
        if _norm(f) not in expected_norm and not _is_under_ignored_dir(f, ignore_dirs)
    )
    for f in extra_files:
        messages.append(f"[WARN] Extra file: {f}")

    if is_ok:
        messages.append("[OK] Folder structure + required files + naming:")

    return is_ok, messages


