import os
import fnmatch


class GitIgnoreFilter:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.rules_cache = {}

    def _load_rules(self, directory):
        if directory in self.rules_cache:
            return self.rules_cache[directory]

        rules = []
        gitignore_path = os.path.join(directory, '.gitignore')
        if os.path.exists(gitignore_path):
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            rules.append(line)
            except Exception:
                pass
        self.rules_cache[directory] = rules
        return rules

    def is_ignored(self, file_or_dir_path, is_dir):
        rel_path = os.path.relpath(file_or_dir_path, self.base_dir)
        if rel_path == '.':
            return False

        current_dir = file_or_dir_path if is_dir else os.path.dirname(file_or_dir_path)
        chain = []
        tmp = current_dir
        while True:
            chain.insert(0, tmp)
            if tmp == self.base_dir or tmp == os.path.dirname(tmp):
                break
            tmp = os.path.dirname(tmp)

        is_ignored_flag = False

        for path_context in chain:
            rules = self._load_rules(path_context)
            if not rules:
                continue

            rel_to_context = os.path.relpath(file_or_dir_path, path_context).replace(os.sep, '/')
            name = os.path.basename(file_or_dir_path)

            for rule in rules:
                negate = rule.startswith('!')
                clean_rule = rule[1:] if negate else rule

                rule_is_dir = clean_rule.endswith('/')
                if rule_is_dir:
                    clean_rule = clean_rule[:-1]

                if not is_dir and rule_is_dir:
                    continue

                matched = False
                if '/' in clean_rule.strip('/'):
                    match_pattern = clean_rule.lstrip('/')
                    if fnmatch.fnmatch(rel_to_context, match_pattern) or fnmatch.fnmatch(rel_to_context, match_pattern + '/*'):
                        matched = True
                else:
                    rule_pattern = clean_rule.lstrip('/')
                    if fnmatch.fnmatch(name, rule_pattern) or fnmatch.fnmatch(rel_to_context, rule_pattern + '/*'):
                        matched = True

                if matched:
                    is_ignored_flag = not negate

        return is_ignored_flag


def _get_ignore_config(config, ignore_dirs, ignore_exts):
    ignore_set = set(config.get("ignored_dirs", []))
    if ignore_dirs:
        for entry in ignore_dirs:
            if entry:
                parts = [p.strip() for p in entry.split(',') if p.strip()]
                ignore_set.update(parts)

    ignored_ext_set = set(config.get("ignored_extensions", []))
    if ignore_exts:
        for entry in ignore_exts:
            if entry:
                parts = [p.strip() for p in entry.split(',') if p.strip()]
                for p in parts:
                    ignored_ext_set.add(p if p.startswith('.') else f'.{p}')

    ignored_files = set(config.get("ignored_files", []))
    return ignore_set, ignored_ext_set, ignored_files


def _is_file_included(filename, root, directory, extension, ignore_set, ignored_ext_set, ignored_files, skip_css):
    if filename in ignored_files:
        return False

    lower = filename.lower()
    if any(lower.endswith(ext) for ext in ignored_ext_set):
        return False

    if extension is None and skip_css and lower.endswith('.css'):
        return False

    if extension is not None and not lower.endswith(extension):
        return False

    if root != directory:
        rel_root = os.path.relpath(root, directory)
        norm_parts = rel_root.split(os.sep)
        if any(part in ignore_set for part in norm_parts):
            return False

    return True
