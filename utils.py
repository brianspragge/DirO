
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

