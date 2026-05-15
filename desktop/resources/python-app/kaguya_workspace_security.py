import os


class WorkspaceAuthorizationError(PermissionError):
    pass


def normalize_path(path, workspace_path):
    if not path:
        raise WorkspaceAuthorizationError("empty_path")
    candidate = path
    if not os.path.isabs(candidate):
        candidate = os.path.join(workspace_path, candidate)
    return os.path.realpath(os.path.abspath(candidate))


def _norm(path):
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


def is_path_inside(path, root):
    try:
        path_norm = _norm(path)
        root_norm = _norm(root)
        return os.path.commonpath([path_norm, root_norm]) == root_norm
    except Exception:
        return False


def _authorized_roots(workspace_path, user_info=None):
    roots = [workspace_path]
    if user_info:
        for item in user_info.get("imported_paths", []) or []:
            if item:
                roots.append(item)
    return [_norm(root) for root in roots if root]


def authorize_path(path, workspace_path, user_info=None, must_exist=False):
    target = normalize_path(path, workspace_path)
    if must_exist and not os.path.exists(target):
        raise WorkspaceAuthorizationError("path_not_found")
    roots = _authorized_roots(workspace_path, user_info)
    target_norm = _norm(target)
    for root in roots:
        try:
            if os.path.commonpath([target_norm, root]) == root:
                return target
        except Exception:
            continue
    raise WorkspaceAuthorizationError("path_outside_workspace")


def authorize_project_root(path, workspace_path, user_info=None, trust=False):
    target = normalize_path(path, workspace_path)
    if not os.path.isdir(target):
        raise WorkspaceAuthorizationError("project_root_not_found")
    if is_path_inside(target, workspace_path):
        return target, False
    if user_info and any(is_path_inside(target, root) for root in user_info.get("imported_paths", []) or []):
        return target, False
    if trust:
        return target, True
    raise WorkspaceAuthorizationError("project_not_trusted")


def add_imported_root(user_info, root_path):
    root = os.path.realpath(os.path.abspath(root_path))
    imported = user_info.setdefault("imported_paths", [])
    if not any(_norm(existing) == _norm(root) for existing in imported):
        imported.append(root)
    return root


def safe_join(root, *parts):
    candidate = os.path.join(root, *parts)
    return authorize_path(candidate, root)
