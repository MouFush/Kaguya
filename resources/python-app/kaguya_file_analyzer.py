#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE 智能文件组织系统 v1.0
参考 Claude Code 的项目结构分析能力

核心功能：
1. 文件分类与多维度筛选（类型/模块/修改时间/大小/依赖）
2. 文件间依赖关系分析与可视化
3. 自动引用建议
4. 项目结构分析与优化推荐
"""

import os
import re
import json
import time
import hashlib
import threading
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from enum import Enum
from datetime import datetime
from collections import defaultdict


class FileCategory(Enum):
    SOURCE = "source"
    HEADER = "header"
    CONFIG = "config"
    DOCUMENTATION = "documentation"
    TEST = "test"
    BUILD = "build"
    ASSET = "asset"
    DATA = "data"
    SCRIPT = "script"
    STYLE = "style"
    TEMPLATE = "template"
    VENDOR = "vendor"
    GENERATED = "generated"
    OTHER = "other"


class DependencyType(Enum):
    IMPORT = "import"
    REQUIRE = "require"
    INCLUDE = "include"
    REFERENCE = "reference"
    INHERIT = "inherit"


EXT_CATEGORY_MAP = {
    ".py": FileCategory.SOURCE, ".js": FileCategory.SOURCE, ".ts": FileCategory.SOURCE,
    ".tsx": FileCategory.SOURCE, ".jsx": FileCategory.SOURCE, ".java": FileCategory.SOURCE,
    ".c": FileCategory.SOURCE, ".cpp": FileCategory.SOURCE, ".h": FileCategory.HEADER,
    ".hpp": FileCategory.HEADER, ".rs": FileCategory.SOURCE, ".go": FileCategory.SOURCE,
    ".rb": FileCategory.SOURCE, ".php": FileCategory.SOURCE, ".swift": FileCategory.SOURCE,
    ".kt": FileCategory.SOURCE, ".cs": FileCategory.SOURCE, ".scala": FileCategory.SOURCE,
    ".json": FileCategory.CONFIG, ".yaml": FileCategory.CONFIG, ".yml": FileCategory.CONFIG,
    ".toml": FileCategory.CONFIG, ".ini": FileCategory.CONFIG, ".cfg": FileCategory.CONFIG,
    ".env": FileCategory.CONFIG, ".conf": FileCategory.CONFIG,
    ".md": FileCategory.DOCUMENTATION, ".rst": FileCategory.DOCUMENTATION,
    ".txt": FileCategory.DOCUMENTATION, ".adoc": FileCategory.DOCUMENTATION,
    "test_": FileCategory.TEST, "_test.": FileCategory.TEST, ".spec.": FileCategory.TEST,
    ".css": FileCategory.STYLE, ".scss": FileCategory.STYLE, ".less": FileCategory.STYLE,
    ".html": FileCategory.TEMPLATE, ".htm": FileCategory.TEMPLATE, ".jinja": FileCategory.TEMPLATE,
    ".j2": FileCategory.TEMPLATE, ".ejs": FileCategory.TEMPLATE, ".hbs": FileCategory.TEMPLATE,
    ".png": FileCategory.ASSET, ".jpg": FileCategory.ASSET, ".jpeg": FileCategory.ASSET,
    ".gif": FileCategory.ASSET, ".svg": FileCategory.ASSET, ".ico": FileCategory.ASSET,
    ".woff": FileCategory.ASSET, ".woff2": FileCategory.ASSET, ".ttf": FileCategory.ASSET,
    ".csv": FileCategory.DATA, ".sql": FileCategory.DATA, ".db": FileCategory.DATA,
    ".sqlite": FileCategory.DATA, ".xml": FileCategory.DATA,
    ".sh": FileCategory.SCRIPT, ".bat": FileCategory.SCRIPT, ".ps1": FileCategory.SCRIPT,
    ".Makefile": FileCategory.BUILD, ".cmake": FileCategory.BUILD, ".gradle": FileCategory.BUILD,
    ".lock": FileCategory.GENERATED, ".min.js": FileCategory.GENERATED,
    ".min.css": FileCategory.GENERATED, ".pyc": FileCategory.GENERATED,
}

IMPORT_PATTERNS = {
    ".py": [
        re.compile(r'^\s*(?:from|import)\s+([a-zA-Z_][\w.]*)', re.MULTILINE),
    ],
    ".js": [
        re.compile(r'(?:import\s+.*?from\s+[\'"]([^\'"]+)[\'"]|require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\))'),
    ],
    ".ts": [
        re.compile(r'(?:import\s+.*?from\s+[\'"]([^\'"]+)[\'"]|require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\))'),
    ],
    ".java": [
        re.compile(r'^\s*import\s+([\w.]+)', re.MULTILINE),
    ],
    ".go": [
        re.compile(r'^\s*import\s+(?:\(.*?\)|"([^"]+)")', re.MULTILINE | re.DOTALL),
    ],
    ".c": [
        re.compile(r'^\s*#include\s*[<"]([^>"]+)[>"]', re.MULTILINE),
    ],
    ".cpp": [
        re.compile(r'^\s*#include\s*[<"]([^>"]+)[>"]', re.MULTILINE),
    ],
    ".rs": [
        re.compile(r'^\s*(?:use|extern\s+crate)\s+([\w:]+)', re.MULTILINE),
    ],
}

IGNORED_DIRS = {
    'node_modules', '.git', '__pycache__', '.venv', 'venv', 'dist', 'build',
    '.next', '.nuxt', 'target', 'out', '.tox', '.mypy_cache', '.pytest_cache',
    '.idea', '.vscode', '.cache', 'vendor', 'Pods', '.gradle', '.mvn',
}

IGNORED_FILES = {
    '.DS_Store', 'Thumbs.db', '.gitkeep', 'package-lock.json', 'yarn.lock',
    'pnpm-lock.yaml', 'Gemfile.lock', 'Cargo.lock', 'poetry.lock',
}


@dataclass
class FileInfo:
    path: str
    name: str
    ext: str
    category: FileCategory
    size: int
    modified_time: float
    created_time: float
    hash: str = ""
    line_count: int = 0
    module: str = ""
    imports: List[str] = field(default_factory=list)
    imported_by: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    is_entry: bool = False
    depth: int = 0


@dataclass
class DependencyEdge:
    source: str
    target: str
    dep_type: DependencyType
    line_number: int = 0
    is_local: bool = False


@dataclass
class StructureRecommendation:
    category: str
    severity: str
    title: str
    description: str
    affected_files: List[str] = field(default_factory=list)
    suggestion: str = ""


class FileAnalyzer:
    def __init__(self, root_path: str):
        self._root = os.path.normpath(root_path)
        self._files: Dict[str, FileInfo] = {}
        self._dependencies: List[DependencyEdge] = []
        self._dep_graph: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_graph: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.Lock()
        self._analyzed = False

    @property
    def root(self) -> str:
        return self._root

    def analyze(self, max_files: int = 5000) -> Dict[str, Any]:
        start = time.time()
        self._scan_files(max_files)
        self._analyze_imports()
        self._detect_modules()
        self._detect_entries()
        self._analyzed = True
        elapsed = time.time() - start
        return {
            "root": self._root,
            "total_files": len(self._files),
            "analysis_time_ms": int(elapsed * 1000),
            "categories": self._get_category_stats(),
            "modules": self._get_module_stats(),
        }

    def _scan_files(self, max_files: int):
        count = 0
        for dirpath, dirnames, filenames in os.walk(self._root):
            dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS and not d.startswith('.')]
            for fname in filenames:
                if fname in IGNORED_FILES:
                    continue
                if count >= max_files:
                    return
                fpath = os.path.join(dirpath, fname)
                try:
                    stat = os.stat(fpath)
                except (OSError, PermissionError):
                    continue
                rel_path = os.path.relpath(fpath, self._root).replace("\\", "/")
                name, ext = os.path.splitext(fname)
                category = self._classify_file(fname, ext, rel_path)
                depth = rel_path.count("/")
                line_count = 0
                if ext in ('.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.c', '.cpp',
                           '.go', '.rs', '.rb', '.php', '.css', '.scss', '.html', '.sh'):
                    try:
                        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                            line_count = sum(1 for _ in f)
                    except Exception:
                        pass
                file_hash = ""
                if stat.st_size < 1024 * 1024:
                    try:
                        with open(fpath, 'rb') as f:
                            file_hash = hashlib.md5(f.read()).hexdigest()[:12]
                    except Exception:
                        pass
                fi = FileInfo(
                    path=rel_path,
                    name=fname,
                    ext=ext.lower(),
                    category=category,
                    size=stat.st_size,
                    modified_time=stat.st_mtime,
                    created_time=stat.st_ctime,
                    hash=file_hash,
                    line_count=line_count,
                    depth=depth,
                )
                self._files[rel_path] = fi
                count += 1

    def _classify_file(self, fname: str, ext: str, rel_path: str) -> FileCategory:
        fname_lower = fname.lower()
        for test_indicator in ('test_', '_test.', '.spec.', '.test.'):
            if test_indicator in fname_lower:
                return FileCategory.TEST
        if fname_lower in ('makefile', 'gnumakefile', 'cmakelists.txt', 'dockerfile'):
            return FileCategory.BUILD
        if fname_lower in ('readme.md', 'readme.txt', 'readme.rst', 'changelog.md',
                           'contributing.md', 'license', 'authors'):
            return FileCategory.DOCUMENTATION
        for key, cat in EXT_CATEGORY_MAP.items():
            if key.startswith('.') and ext.lower() == key:
                return cat
            elif not key.startswith('.') and key in fname_lower:
                return cat
        return FileCategory.OTHER

    def _analyze_imports(self):
        for rel_path, fi in self._files.items():
            if fi.ext not in IMPORT_PATTERNS:
                continue
            fpath = os.path.join(self._root, rel_path)
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception:
                continue
            patterns = IMPORT_PATTERNS.get(fi.ext, [])
            for pattern in patterns:
                for match in pattern.finditer(content):
                    groups = [g for g in match.groups() if g]
                    if not groups:
                        continue
                    import_path = groups[0]
                    resolved = self._resolve_import(import_path, fi)
                    if resolved:
                        edge = DependencyEdge(
                            source=rel_path,
                            target=resolved,
                            dep_type=DependencyType.IMPORT,
                            is_local=True,
                        )
                        self._dependencies.append(edge)
                        self._dep_graph[rel_path].add(resolved)
                        self._reverse_graph[resolved].add(rel_path)
                        fi.imports.append(resolved)
                        target_fi = self._files.get(resolved)
                        if target_fi:
                            target_fi.imported_by.append(rel_path)

    def _resolve_import(self, import_path: str, source: FileInfo) -> Optional[str]:
        if import_path.startswith('.'):
            source_dir = os.path.dirname(source.path)
            parts = import_path.split('/')
            resolved = os.path.normpath(os.path.join(source_dir, *parts)).replace("\\", "/")
            for ext in ('', '.py', '.js', '.ts', '.tsx', '.jsx'):
                candidate = resolved + ext
                if candidate in self._files:
                    return candidate
            index_path = resolved + '/index'
            for ext in ('.js', '.ts', '.tsx'):
                if index_path + ext in self._files:
                    return index_path + ext
        else:
            parts = import_path.replace('/', os.sep).split(os.sep)
            if len(parts) >= 1:
                top = parts[0]
                for fp, fi in self._files.items():
                    fp_parts = fp.split('/')
                    if len(fp_parts) > 1 and fp_parts[0] == top:
                        return fp
        return None

    def _detect_modules(self):
        dir_files = defaultdict(list)
        for fp, fi in self._files.items():
            parts = fp.split('/')
            if len(parts) > 1:
                module = parts[0]
            else:
                module = "root"
            fi.module = module
            dir_files[module].append(fp)

    def _detect_entries(self):
        entry_names = {
            'main.py', 'main.js', 'main.ts', 'index.py', 'index.js', 'index.ts',
            'app.py', 'app.js', 'app.ts', 'server.py', 'server.js',
            '__init__.py', '__main__.py', 'manage.py', 'setup.py',
            'cli.py', 'cli.js', 'cli.ts', 'run.py',
            'main.go', 'main.rs', 'Main.java',
            'index.tsx', 'index.jsx', 'App.tsx', 'App.jsx',
        }
        for fp, fi in self._files.items():
            if fi.name in entry_names:
                fi.is_entry = True
                fi.tags.append('entry-point')

    def _get_category_stats(self) -> Dict[str, int]:
        stats = defaultdict(int)
        for fi in self._files.values():
            stats[fi.category.value] += 1
        return dict(stats)

    def _get_module_stats(self) -> Dict[str, Dict]:
        stats = defaultdict(lambda: {"files": 0, "size": 0, "categories": defaultdict(int)})
        for fi in self._files.values():
            m = fi.module
            stats[m]["files"] += 1
            stats[m]["size"] += fi.size
            stats[m]["categories"][fi.category.value] += 1
        result = {}
        for m, s in stats.items():
            result[m] = {"files": s["files"], "size": s["size"],
                         "categories": dict(s["categories"])}
        return result

    def get_files(self, category: str = None, module: str = None,
                  ext: str = None, sort_by: str = "path",
                  sort_order: str = "asc", limit: int = 100,
                  offset: int = 0, query: str = "") -> Dict[str, Any]:
        files = list(self._files.values())
        if category:
            try:
                cat = FileCategory(category)
                files = [f for f in files if f.category == cat]
            except ValueError:
                pass
        if module:
            files = [f for f in files if f.module == module]
        if ext:
            files = [f for f in files if f.ext == ext.lower()]
        if query:
            q = query.lower()
            files = [f for f in files if q in f.path.lower() or q in f.name.lower()]
        sort_key_map = {
            "path": lambda f: f.path,
            "name": lambda f: f.name,
            "size": lambda f: f.size,
            "modified": lambda f: f.modified_time,
            "category": lambda f: f.category.value,
            "module": lambda f: f.module,
            "lines": lambda f: f.line_count,
        }
        key_fn = sort_key_map.get(sort_by, lambda f: f.path)
        files.sort(key=key_fn, reverse=(sort_order == "desc"))
        total = len(files)
        page = files[offset:offset + limit]
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "files": [asdict(f) for f in page],
        }

    def get_dependencies(self, path: str = None, direction: str = "outgoing",
                         depth: int = 1) -> Dict[str, Any]:
        if path:
            if direction == "outgoing":
                nodes = self._get_deps_recursive(path, self._dep_graph, depth)
            else:
                nodes = self._get_deps_recursive(path, self._reverse_graph, depth)
            edges = [asdict(e) for e in self._dependencies
                     if (direction == "outgoing" and e.source in nodes) or
                     (direction == "incoming" and e.target in nodes)]
            return {"root": path, "direction": direction, "nodes": list(nodes), "edges": edges}
        return {
            "total_edges": len(self._dependencies),
            "edges": [asdict(e) for e in self._dependencies[:200]],
            "stats": {
                "avg_deps_per_file": len(self._dependencies) / max(len(self._files), 1),
                "max_depth": self._get_max_dep_depth(),
            }
        }

    def _get_deps_recursive(self, start: str, graph: Dict[str, Set[str]],
                            depth: int) -> Set[str]:
        visited = {start}
        current_level = {start}
        for _ in range(depth):
            next_level = set()
            for node in current_level:
                for dep in graph.get(node, set()):
                    if dep not in visited:
                        visited.add(dep)
                        next_level.add(dep)
            current_level = next_level
            if not next_level:
                break
        return visited

    def _get_max_dep_depth(self) -> int:
        visited = set()
        max_depth = 0
        for start in self._files:
            if start in visited:
                continue
            depth = 0
            current = start
            while current and current not in visited:
                visited.add(current)
                deps = self._dep_graph.get(current, set())
                current = next(iter(deps)) if deps else None
                depth += 1
            max_depth = max(max_depth, depth)
        return min(max_depth, 50)

    def get_reference_suggestions(self, path: str, limit: int = 10) -> List[Dict]:
        fi = self._files.get(path)
        if not fi:
            return []
        suggestions = []
        for dep_path in fi.imports:
            dep_fi = self._files.get(dep_path)
            if dep_fi:
                for reverse_dep in dep_fi.imported_by:
                    if reverse_dep != path and reverse_dep not in fi.imports:
                        rfi = self._files.get(reverse_dep)
                        if rfi:
                            common = len(set(fi.imports) & set(rfi.imports))
                            suggestions.append({
                                "file": reverse_dep,
                                "reason": f"Shared dependency: {dep_path}",
                                "common_deps": common,
                                "category": rfi.category.value,
                            })
        suggestions.sort(key=lambda s: s["common_deps"], reverse=True)
        return suggestions[:limit]

    def get_structure_recommendations(self) -> List[Dict]:
        recs = []
        self._check_deep_nesting(recs)
        self._check_large_files(recs)
        self._check_circular_deps(recs)
        self._check_missing_init(recs)
        self._check_orphan_files(recs)
        self._check_test_coverage(recs)
        return [asdict(r) if isinstance(r, StructureRecommendation) else r for r in recs]

    def _check_deep_nesting(self, recs: list):
        deep = [f for f in self._files.values() if f.depth > 5]
        if deep:
            recs.append(StructureRecommendation(
                category="structure", severity="warning",
                title="深层目录嵌套",
                description=f"发现 {len(deep)} 个文件嵌套深度超过5层",
                affected_files=[f.path for f in deep[:10]],
                suggestion="考虑扁平化目录结构，将深层文件提升到更浅的层级",
            ))

    def _check_large_files(self, recs: list):
        large = [f for f in self._files.values() if f.line_count > 500]
        if large:
            recs.append(StructureRecommendation(
                category="maintainability", severity="info",
                title="大文件",
                description=f"发现 {len(large)} 个文件超过500行",
                affected_files=[f"{f.path} ({f.line_count}行)" for f in sorted(large, key=lambda x: -x.line_count)[:10]],
                suggestion="考虑将大文件拆分为更小的模块，提高可维护性",
            ))

    def _check_circular_deps(self, recs: list):
        cycles = self._find_cycles()
        if cycles:
            recs.append(StructureRecommendation(
                category="architecture", severity="error",
                title="循环依赖",
                description=f"发现 {len(cycles)} 个循环依赖",
                affected_files=[f"{' → '.join(c)}" for c in cycles[:5]],
                suggestion="重构代码消除循环依赖，考虑引入接口层或事件系统",
            ))

    def _check_missing_init(self, recs: list):
        py_dirs = set()
        for fp, fi in self._files.items():
            if fi.ext == '.py' and '/' in fp:
                py_dirs.add(fp.rsplit('/', 1)[0])
        missing = []
        for d in py_dirs:
            init_path = d + '/__init__.py'
            if init_path not in self._files:
                missing.append(d)
        if missing:
            recs.append(StructureRecommendation(
                category="structure", severity="info",
                title="缺少 __init__.py",
                description=f"发现 {len(missing)} 个Python目录缺少 __init__.py",
                affected_files=missing[:10],
                suggestion="添加 __init__.py 使目录成为合法的Python包",
            ))

    def _check_orphan_files(self, recs: list):
        orphans = [f for f in self._files.values()
                   if not f.imported_by and not f.imports and f.category == FileCategory.SOURCE]
        if len(orphans) > 5:
            recs.append(StructureRecommendation(
                category="structure", severity="info",
                title="孤立文件",
                description=f"发现 {len(orphans)} 个源文件无任何依赖关系",
                affected_files=[f.path for f in orphans[:10]],
                suggestion="检查这些文件是否仍在使用，考虑清理或整合",
            ))

    def _check_test_coverage(self, recs: list):
        source_count = sum(1 for f in self._files.values() if f.category == FileCategory.SOURCE)
        test_count = sum(1 for f in self._files.values() if f.category == FileCategory.TEST)
        if source_count > 10 and test_count == 0:
            recs.append(StructureRecommendation(
                category="quality", severity="warning",
                title="缺少测试",
                description=f"项目有 {source_count} 个源文件但无测试文件",
                suggestion="添加单元测试以提高代码质量和可维护性",
            ))
        elif source_count > 0 and test_count > 0:
            ratio = test_count / source_count
            if ratio < 0.2:
                recs.append(StructureRecommendation(
                    category="quality", severity="info",
                    title="测试覆盖率低",
                    description=f"测试/源文件比率为 {ratio:.1%}",
                    suggestion="增加测试覆盖率，目标至少30%",
                ))

    def _find_cycles(self, max_cycles: int = 10) -> List[List[str]]:
        cycles = []
        visited = set()
        for start in self._files:
            if start in visited:
                continue
            path = []
            path_set = set()
            self._dfs_cycles(start, path, path_set, visited, cycles, max_cycles)
            if len(cycles) >= max_cycles:
                break
        return cycles

    def _dfs_cycles(self, node: str, path: list, path_set: set,
                    global_visited: set, cycles: list, max_cycles: int):
        if len(cycles) >= max_cycles:
            return
        if node in path_set:
            cycle_start = path.index(node)
            cycle = path[cycle_start:] + [node]
            cycles.append(cycle)
            return
        if node in global_visited:
            return
        path.append(node)
        path_set.add(node)
        for dep in self._dep_graph.get(node, set()):
            self._dfs_cycles(dep, path, path_set, global_visited, cycles, max_cycles)
        path.pop()
        path_set.discard(node)
        global_visited.add(node)

    def get_tree(self, max_depth: int = 3) -> Dict[str, Any]:
        tree = {"name": os.path.basename(self._root), "type": "directory", "children": []}
        for fp, fi in sorted(self._files.items()):
            parts = fp.split('/')
            if len(parts) > max_depth:
                parts = parts[:max_depth]
            current = tree
            for i, part in enumerate(parts):
                is_file = (i == len(parts) - 1) and (fp.count('/') < max_depth or len(fp.split('/')) == i + 1)
                existing = None
                for child in current.get("children", []):
                    if child["name"] == part:
                        existing = child
                        break
                if existing:
                    current = existing
                else:
                    node_type = "file" if is_file else "directory"
                    node = {"name": part, "type": node_type, "children": []}
                    if is_file:
                        node["category"] = fi.category.value
                        node["size"] = fi.size
                        node["lines"] = fi.line_count
                        del node["children"]
                    current.setdefault("children", []).append(node)
                    current = node
        return tree

    def get_stats(self) -> Dict[str, Any]:
        total_size = sum(f.size for f in self._files.values())
        total_lines = sum(f.line_count for f in self._files.values())
        return {
            "total_files": len(self._files),
            "total_size": total_size,
            "total_lines": total_lines,
            "total_deps": len(self._dependencies),
            "categories": self._get_category_stats(),
            "modules": len(set(f.module for f in self._files.values())),
            "entry_points": sum(1 for f in self._files.values() if f.is_entry),
            "analyzed": self._analyzed,
        }


_file_analyzers: Dict[str, FileAnalyzer] = {}
_analyzer_lock = threading.Lock()


def get_analyzer(project_path: str) -> FileAnalyzer:
    norm_path = os.path.normpath(project_path)
    with _analyzer_lock:
        if norm_path not in _file_analyzers:
            _file_analyzers[norm_path] = FileAnalyzer(norm_path)
        return _file_analyzers[norm_path]
