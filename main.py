import sys
import os
import shutil
import hashlib
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                              QPushButton, QTextEdit, QLabel, QFileDialog, QCheckBox)

def select_folder(parent):
    dialog = QFileDialog(parent, "Select Directory")
    dialog.setFileMode(QFileDialog.Directory)
    dialog.setOption(QFileDialog.DontUseNativeDialog, True) 
    if dialog.exec():
        selected = dialog.selectedFiles()
        current_dir = dialog.directory().absolutePath()
        print(f":Selected: {selected}, Current: {current_dir}")
        if selected and selected[0] and len(selected[0].split('/')) > len(current_dir.split('/')):
            return selected[0]
        return current_dir
    return None

def get_file_info(folder_path, recursive=False):
    files = []
    seen_names = {}
    duplicates = []

    def scan_dir(path, top_level_only=True):
        with os.scandir(path) as entries:
            for entry in entries:
                if entry.is_file():
                    yield entry.path
                elif not top_level_only and entry.is_dir():
                    yield from scan_dir(entry.path, top_level_only)

    for file_path in scan_dir(folder_path, top_level_only=not recursive):
        name = os.path.basename(file_path)
        ext = os.path.splitext(name)[1].lower() or ".no_extension"
        words = name.rsplit('.', 1)[0].split()

        if name in seen_names:
            duplicates.append(file_path)
        else:
            seen_names[name] = file_path
            files.append({
                "path": file_path,
                "name": name,
                "ext": ext,
                "words": words
            })

    return files, duplicates

def hash_file(file_path):
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def sort_by_type(files, recursive=False, base_path=None, check_contents=False):
    suggestions = {}
    by_type = {}
    for f in files:
        by_type.setdefault(f["ext"], []).append(f["path"])

    if recursive and base_path:
        for ext, paths in by_type.items():
            if len(paths) > 1:
                suggestions[f"Type_{ext[1:]}" if ext != ".no_extension" else "No_Extension"] = paths
            else:
                suggestions.setdefault(base_path, []).append(paths[0])
    else:
        for ext, paths in by_type.items():
            if len(paths) > 1:
                suggestions[f"Type_{ext[1:]}" if ext != ".no_extension" else "No_Extension"] = paths
    return suggestions

def sort_by_similarity(files, check_contents=False):
    def similarity_score(key1, key2):
        if check_contents:
            s1, s2 = key1, key2
            if s1 == s2:
                return 100
            common = sum(1 for c1, c2 in zip(s1, s2) if c1 == c2)
            total = max(len(s1), len(s2))
            return (common / total) * 100
        else:
            s1 = key1.rsplit('.', 1)[0].lower()
            s2 = key2.rsplit('.', 1)[0].lower()
            if abs(len(s1) - len(s2)) > max(len(s1), len(s2)) // 2:
                return 0
            common = sum(1 for c in set(s1) if c in s2)
            total = max(len(s1), len(s2))
            score = (common / total) * 100 if total > 0 else 0
            prefix_len = 0
            for c1, c2 in zip(s1, s2):
                if c1 != c2:
                    break
                prefix_len += 1
            if prefix_len >= 3:
                score = min(100, score + prefix_len * 5)
            return score

    suggestions = {}
    processed = set()
    hashes = {}

    for i, f1 in enumerate(files):
        if f1["path"] in processed:
            continue
        group = [f1["path"]]
        key1 = hash_file(f1["path"]) if check_contents else f1["name"]
        if check_contents:
            hashes[f1["path"]] = key1
        folder_name = key1[:8] if check_contents else f1["name"].rsplit('.', 1)[0][:5]

        for f2 in files[i+1:]:
            if f2["path"] in processed:
                continue
            key2 = hashes.get(f2["path"], hash_file(f2["path"])) if check_contents else f2["name"]
            if check_contents and f2["path"] not in hashes:
                hashes[f2["path"]] = key2
            score = similarity_score(key1, key2)
            if score >= 60:
                group.append(f2["path"])
                processed.add(f2["path"])

        if len(group) > 1:
            suggestions[f"Similar_{folder_name}"] = group
        processed.add(f1["path"])

    return suggestions

def sort_all_files(files, check_contents=False):
    if files:
        return {"All_Files": [f["path"] for f in files]}
    return {}

sort_methods = {
    "Type": sort_by_type,
    "Similarity": sort_by_similarity,
    "All Files": sort_all_files
}

def organize_files(suggestions, recursive=False, base_path=None):
    moved_files = []
    root_path = base_path if base_path else suggestions[next(iter(suggestions))][0].rsplit('/', 1)[0]

    for folder_name, files in suggestions.items():
        new_folder = folder_name if folder_name == root_path else os.path.join(root_path, folder_name)
        os.makedirs(new_folder, exist_ok=True)
        for file_path in files:
            dest_path = os.path.join(new_folder, os.path.basename(file_path))
            try:
                shutil.move(file_path, dest_path)
                moved_files.append(dest_path)
            except Exception as e:
                print(f"Error moving {file_path}: {e}")
    for dest_path in moved_files:
        while not os.path.exists(dest_path):
            pass

    if recursive:
        empty_folders_found = False
        for root, dirs, _ in os.walk(root_path, topdown=False):
            if root != root_path and not os.listdir(root):
                empty_folders_found = True
                break
        if empty_folders_found:
            empty_folders = os.path.join(root_path, "empty_folders")
            os.makedirs(empty_folders, exist_ok=True)
            for root, dirs, _ in os.walk(root_path, topdown=False):
                if root != root_path and root != empty_folders and not os.listdir(root):
                    try:
                        shutil.move(root, os.path.join(empty_folders, os.path.basename(root)))
                    except Exception as e:
                        print(f"Error moving folder {root}: {e}")

def move_duplicates(duplicates, base_path, check_contents=False):
    if not duplicates:
        return
    dup_folder = os.path.join(base_path, "duplicates")
    os.makedirs(dup_folder, exist_ok=True)
    moved_files = []

    if check_contents:
        by_hash = {}
        for path in duplicates:
            if os.path.getsize(path) > 0:
                hash_val = hash_file(path)
                by_hash.setdefault(hash_val, []).append(path)
        final_dups = [path for paths in by_hash.values() if len(paths) > 1 for path in paths]
    else:
        final_dups = duplicates

    for i, path in enumerate(final_dups):
        dest_path = os.path.join(dup_folder, f"dup_{i}_{os.path.basename(path)}")
        try:
            shutil.move(path, dest_path)
            moved_files.append(dest_path)
        except Exception as e:
            print(f"Error moving duplicate {path}: {e}")
    for dest_path in moved_files:
        while not os.path.exists(dest_path):
            pass

def main():
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("File Explorer and Organizer")
    window.setGeometry(100, 100, 800, 600)

    widget = QWidget()
    window.setCentralWidget(widget)
    layout = QVBoxLayout(widget)

    select_btn = QPushButton("Select Folder")
    cleanup_checkbox = QCheckBox("Include Subfolders and Cleanup")
    content_checkbox = QCheckBox("Check Contents")
    results_text = QTextEdit()
    results_text.setReadOnly(True)
    status_label = QLabel("")

    layout.addWidget(select_btn)
    layout.addWidget(cleanup_checkbox)
    layout.addWidget(content_checkbox)
    layout.addWidget(results_text)
    layout.addWidget(status_label)

    buttons = {}
    for name in sort_methods:
        btn = QPushButton(f"Organize by {name}")
        btn.setEnabled(False)
        layout.addWidget(btn)
        buttons[name] = btn

    dup_btn = QPushButton("Sort Duplicates")
    dup_btn.setEnabled(False)
    layout.addWidget(dup_btn)

    current_folder = [None]
    current_files = [None]
    current_duplicates = [None]
    current_suggestions = [None]

    def on_select():
        folder = select_folder(window)
        if folder:
            current_folder[0] = folder
            status_label.setText(f"selected: {folder} (click OK to confirm)")
            files, duplicates = get_file_info(folder, recursive=cleanup_checkbox.isChecked())
            current_files[0] = files
            current_duplicates[0] = duplicates
            suggestions = {
                "Type": sort_by_type(files, recursive=cleanup_checkbox.isChecked(), base_path=folder),
                "Similarity": sort_by_similarity(files, check_contents=content_checkbox.isChecked()),
                "All Files": sort_all_files(files)
            }
            current_suggestions[0] = suggestions

            scope = "Recursive" if cleanup_checkbox.isChecked() else "Top-Level Only"
            text = f"Analysis Results of {len(files) + len(duplicates)} Total Files ({scope}):\n"
            text += f"Unique Files: {len(files)}, Duplicates Found: {len(duplicates)}\n\nYou Currently Have:\n"
            by_type = {}
            for f in files:
                by_type.setdefault(f["ext"], []).append(f["path"])
            for ext, paths in sorted(by_type.items()):
                text += f"{len(paths)} {ext} file(s)\n"

            if duplicates:
                text += "\nDuplicates (Not Yet Sorted):\n"
                for dup_path in duplicates:
                    text += f"{dup_path}\n"

            text += "\nOrganization Options:\n"
            for name, suggestion in suggestions.items():
                if not suggestion:
                    continue
                num_groups = len([k for k in suggestion if k != folder])
                largest_group = max(len(files) for files in suggestion.values()) if suggestion else 0
                text += f"By {name} ({num_groups} groups, largest: {largest_group}):\n"
                for folder_name, paths in suggestion.items():
                    samples = [os.path.basename(p) for p in paths[:2]]
                    if folder_name == folder:
                        text += f"  Main Directory: {len(paths)} files (e.g., {', '.join(samples)})\n"
                    else:
                        text += f"  {folder_name}: {len(paths)} files (e.g., {', '.join(samples)})\n"

            text += "\nRecommendation: "
            if len(suggestions["Type"]) > 2:
                text += "'Type' - Best for organizing varied file types."
            elif len(suggestions["Similarity"]) > 1 and len(files) - sum(len(v) for v in suggestions["Similarity"].values()) < len(files) // 2:
                text += "'Similarity' - Good for grouping similar filenames."
            else:
                text += "'All Files' - Simplest consolidation into one folder."

            results_text.setText(text)
            for btn in buttons.values():
                btn.setEnabled(True)
            dup_btn.setEnabled(bool(duplicates))
            status_label.setText(f"Selected: {folder}")

    def reset_and_reanalyze():
        if current_folder[0]:
            on_select()

    def make_organize(name):
        def on_organize():
            if current_suggestions[0]:
                suggestions = current_suggestions[0]
                organize_files(suggestions[name], recursive=cleanup_checkbox.isChecked(), 
                             base_path=current_folder[0])
                status_label.setText(f"Files organized by {name.lower()} successfully!")
                reset_and_reanalyze()
        return on_organize

    def on_sort_duplicates():
        if current_duplicates[0] and current_folder[0]:
            move_duplicates(current_duplicates[0], current_folder[0], content_checkbox.isChecked())
            status_label.setText("Duplicates sorted successfully!")
            reset_and_reanalyze()

    select_btn.clicked.connect(on_select)
    for name, btn in buttons.items():
        btn.clicked.connect(make_organize(name))
    dup_btn.clicked.connect(on_sort_duplicates)

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
