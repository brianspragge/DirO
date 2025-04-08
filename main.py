# DirO stands for Directory Organizer.
#      it is a file/folder sorting application.
#      the plan is to release it cross-platform.

import sys
import os
import shutil
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                              QPushButton, QTextEdit, QLabel, QFileDialog, QCheckBox)

def select_folder(parent):
    return QFileDialog.getExistingDirectory(parent, "Select Directory")

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

def sort_by_type(files, recursive=False, base_path=None):
    suggestions = {}
    by_type = {}
    for f in files:
        by_type.setdefault(f["ext"], []).append(f["path"])

    if recursive and base_path:
        # When recursive, unique extensions go to base_path, 2+ go to Type_* folders
        for ext, paths in by_type.items():
            if len(paths) > 1:
                suggestions[f"Type_{ext[1:]}" if ext != ".no_extension" else "No_Extension"] = paths
            else:
                # Move unique extension files to base_path (no folder)
                suggestions.setdefault(base_path, []).append(paths[0])
    else:
        # Non-recursive: only group 2+ files, leave others in place
        for ext, paths in by_type.items():
            if len(paths) > 1:
                suggestions[f"Type_{ext[1:]}" if ext != ".no_extension" else "No_Extension"] = paths

    return suggestions

def sort_by_similarity(files):
    def similarity_score(name1, name2):
        s1 = name1.rsplit('.', 1)[0].lower()
        s2 = name2.rsplit('.', 1)[0].lower()

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

    for i, f1 in enumerate(files):
        if f1["path"] in processed:
            continue
        group = [f1["path"]]
        folder_name = f1["name"].rsplit('.', 1)[0][:5]

        for f2 in files[i+1:]:
            if f2["path"] in processed:
                continue
            score = similarity_score(f1["name"], f2["name"])
            if score >= 60:
                group.append(f2["path"])
                processed.add(f2["path"])

        if len(group) > 1:
            suggestions[f"Similar_{folder_name}"] = group
        processed.add(f1["path"])

    return suggestions

def sort_all_files(files):
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
    # Use provided base_path (selected folder) instead of first file's parent
    root_path = base_path if base_path else suggestions[next(iter(suggestions))][0].rsplit('/', 1)[0]

    for folder_name, files in suggestions.items():
        # If folder_name is base_path, move files there directly
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
            pass  # Wait for move to complete

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

def move_duplicates(duplicates, base_path):
    if not duplicates:
        return
    dup_folder = os.path.join(base_path, "duplicates")
    os.makedirs(dup_folder, exist_ok=True)
    moved_files = []
    for dup_path in duplicates:
        dest_path = os.path.join(dup_folder, os.path.basename(dup_path))
        try:
            shutil.move(dup_path, dest_path)
            moved_files.append(dest_path)
        except Exception as e:
            print(f"Error moving duplicate {dup_path}: {e}")
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
    results_text = QTextEdit()
    results_text.setReadOnly(True)
    status_label = QLabel("")
    cleanup_checkbox = QCheckBox("Include Subfolders and Cleanup")

    layout.addWidget(select_btn)
    layout.addWidget(cleanup_checkbox)
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
            files, duplicates = get_file_info(folder, recursive=cleanup_checkbox.isChecked())
            current_files[0] = files
            current_duplicates[0] = duplicates
            suggestions = {
                name: method(files, recursive=cleanup_checkbox.isChecked(), base_path=folder)
                if name == "Type" else method(files)
                for name, method in sort_methods.items()
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
                num_groups = len([k for k in suggestion if k != folder])  # Exclude base_path as a "group"
                largest_group = max(len(files) for files in suggestion.values()) if suggestion else 0
                text += f"By {name} ({num_groups} groups, largest: {largest_group}):\n"
                for folder_name, paths in suggestion.items():
                    samples = [os.path.basename(p) for p in paths[:2]]  # Limit to 2 samples
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
            current_files[0] = None
            current_duplicates[0] = None
            current_suggestions[0] = None
            on_select()

    def make_organize(name):
        def on_organize():
            if current_suggestions[0]:
                suggestions = current_suggestions[0]
                organize_files(suggestions[name], recursive=cleanup_checkbox.isChecked(), base_path=current_folder[0])
                status_label.setText(f"Files organized by {name.lower()} successfully!")
                reset_and_reanalyze()
        return on_organize

    def on_sort_duplicates():
        if current_duplicates[0] and current_folder[0]:
            move_duplicates(current_duplicates[0], current_folder[0])
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
