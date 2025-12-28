
from colorama import init, Fore, Style
init(autoreset=True)
import json
from pathlib import Path
from validator import build_reference_snapshot, validate_asset

CONFIG_FILE = Path(__file__).with_name("config.json")

def print_colored(msg: str) -> None:
    if msg.startswith("[ERROR]"):
        print(Fore.RED + msg + Style.RESET_ALL)
    elif msg.startswith("[OK]"):
        print(Fore.GREEN + msg + Style.RESET_ALL)
    elif msg.startswith("[WARN]"):
        print(Fore.YELLOW + msg + Style.RESET_ALL)
    elif msg.startswith("[HINT]"):
        print(Fore.CYAN + msg + Style.RESET_ALL)
    else:
        print_colored(msg)

def load_config():
    if not CONFIG_FILE.exists():
        return {}

    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        print("[WARN] config.json is broken, using empty config.")
        return {}

def save_config(config):    #saves config
    CONFIG_FILE.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

def ask_reference_path():  # returns reference folder path
    cfg = load_config()
    saved_ref = cfg.get("reference_folder_path")

    if saved_ref:
        print(f"Saved reference folder: {saved_ref}")

        while True:
            choice = input("Use this reference? (Y/N): ").strip().lower()

            if choice in ("y", "yes"):
                return saved_ref
            elif choice in ("n", "no"):
                break
            else:
                print("Invalid input. Please enter Y or N.")

    while True:
        new_ref = input("Enter reference folder path: ").strip()
        if new_ref:
            cfg["reference_folder_path"] = new_ref
            save_config(cfg)
            print(Fore.GREEN + "[OK]" + Fore.RESET + " Reference path saved to config.json")
            return new_ref
        else:
            print("Reference path cannot be empty.")

def get_ignore_dirs(cfg: dict) -> list[str]:
    return cfg.get("ignore_dirs", []) or []

def add_ignore_dir(cfg: dict, folder: str):
    ignores = set(get_ignore_dirs(cfg))
    ignores.add(folder)
    cfg["ignore_dirs"] = sorted(ignores)
    save_config(cfg)

def suggest_ignore_folder(messages: list[str], threshold: int = 3, already_ignored=None):
    already_ignored = set(already_ignored or [])
    counts = {}

    for msg in messages:
        path = None


        if msg.startswith("[ERROR] Missing file: "):
            path = msg.removeprefix("[ERROR] Missing file: ").strip()

        elif msg.startswith("[ERROR] Wrong naming in '"):

            try:
                path = msg.split(":", 2)[1].strip()
            except IndexError:
                path = None

        if not path:
            continue

        path = path.replace("\\", "/")

        if "/" not in path:
            continue

        top = path.split("/", 1)[0]
        if top in already_ignored:
            continue

        counts[top] = counts.get(top, 0) + 1

    if not counts:
        return None

    folder, cnt = max(counts.items(), key=lambda x: x[1])
    return (folder, cnt) if cnt >= threshold else None

def clear_settings():
    cfg = load_config()
    changed = False

    if "reference_folder_path" in cfg:
        del cfg["reference_folder_path"]
        changed = True

    if "ignore_dirs" in cfg:
        del cfg["ignore_dirs"]
        changed = True

    if changed:
        save_config(cfg)
        print_colored("[OK] Settings cleared (reference path + ignored folders).")
    else:
        print_colored("[WARN] Nothing to clear.")

def main():
    print("Asset Validation Tool started")

    # CREATING REFERENCE FOLDER

    reference_folder_path = ask_reference_path()

    ref_snapshot, ref_messages = build_reference_snapshot(reference_folder_path)
    print("--- REFERENCE REPORT ---")
    for msg in ref_messages:
        print_colored(msg)
    if ref_snapshot is None:
        print("RESULT: FAIL (Reference snapshot not built)")
        return 1
    print("REFERENCE: OK")

    # ASSET TO VALIDATE LOOP

    cfg = load_config()
    session_ignore_dirs = set(get_ignore_dirs(cfg))

    asset_folder_path = None

    while True:
        if not asset_folder_path:
            asset_folder_path = input("Enter asset folder path: ").strip()
            asset_folder_path = asset_folder_path if asset_folder_path else None
            if not asset_folder_path:
                print("Asset folder path cannot be empty.")
                continue

        asset_folder = Path(asset_folder_path)
        asset_name = asset_folder.name

        is_ok, messages = validate_asset(asset_name, asset_folder_path, ref_snapshot, ignore_dirs=list(session_ignore_dirs))

        print("--- ASSET REPORT ---")
        for msg in messages:
            print_colored(msg)

        if is_ok:
            print(Fore.GREEN + "RESULT: PASS" + Style.RESET_ALL)
        else:
            print(Fore.RED + "RESULT: FAIL" + Style.RESET_ALL)

        # --- SMART IGNORE SUGGESTION ---
        suggestion = suggest_ignore_folder(
            messages,
            threshold=3,
            already_ignored=session_ignore_dirs
        )

        if suggestion:
            folder, cnt = suggestion
            print(f"\n[HINT] Many file/naming issues under '{folder}' ({cnt}).")
            while True:
                choice = input("Ignore this folder? [1] Once  [2] Always (remember)  [3] No: ").strip()
                if choice == "1":
                    session_ignore_dirs.add(folder)
                    print(f"[OK] Ignoring '{folder}' for this session.")
                    break
                elif choice == "2":
                    session_ignore_dirs.add(folder)
                    add_ignore_dir(cfg, folder)
                    print(f"[OK] Ignoring '{folder}' and remembered.")
                    break
                elif choice == "3":
                    break
                else:
                    print("Invalid input. Enter 1/2/3.")


            if choice in ("1", "2"):
                print("\n--- RE-RUN (with ignore applied) ---")
                is_ok, messages = validate_asset(asset_name, asset_folder_path, ref_snapshot,
                                                 ignore_dirs=list(session_ignore_dirs))
                print("--- ASSET REPORT ---")
                for msg in messages:
                    print_colored(msg)
                if is_ok:
                    print(Fore.GREEN + "RESULT: PASS" + Fore.RESET)
                else:
                    print(Fore.RED + "RESULT: FAIL" + Fore.RESET)

        #VALIDATE AGAIN?

        while True:
            choice = input("\n[R]evalidate / [N]ew asset / [C]lear settings / [Q]uit: ").strip().lower()
            if choice == "r":
                break
            elif choice == "n":
                asset_folder_path = None
                break
            elif choice == "c":
                confirm = input(
                    "Clear saved reference path and ignored folders? (Y/N): "
                ).strip().lower()

                if confirm in ("y", "yes"):
                    clear_settings()
                    session_ignore_dirs.clear()
                    asset_folder_path = None
                else:
                    print_colored("[WARN] Cancelled.")
            elif choice == "q":
                print("Exit.")
                return 0
            else:
                print("Invalid input.")



if __name__ == "__main__":
    import sys
    sys.exit(main())
