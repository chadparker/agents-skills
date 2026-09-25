import os
import re
import subprocess
import tempfile
from pathlib import Path

SCRIPT = str(Path(__file__).resolve().with_name('repos-sync.sh'))
ROOT = Path(tempfile.mkdtemp(prefix='repos-sync-tests-'))
REPOS = ROOT / 'repos'
REPOS.mkdir()
ENV = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
           GIT_AUTHOR_NAME='Sync Test', GIT_AUTHOR_EMAIL='sync@example.invalid',
           GIT_COMMITTER_NAME='Sync Test', GIT_COMMITTER_EMAIL='sync@example.invalid',
           GIT_TERMINAL_PROMPT='0')
for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR'):
    ENV.pop(key, None)


def git(repo, *args, ok=True):
    result = subprocess.run(['git', '-C', str(repo), *args], env=ENV, text=True, capture_output=True)
    if ok and result.returncode:
        raise AssertionError(f'git {args}: {result.stderr}')
    return result.stdout.strip() if ok else result


def fixture(name):
    remote = ROOT / (name + '.git')
    remote.mkdir()
    git(remote, 'init', '--bare', '--initial-branch=main')
    repo = REPOS / name
    git(ROOT, 'clone', str(remote), str(repo))
    (repo / 'tracked').write_text('base\n')
    git(repo, 'add', '.')
    git(repo, 'commit', '-m', 'base')
    git(repo, 'push', '-u', 'origin', 'main')
    return repo


def advance(repo):
    # Publish a new commit without changing this clone's HEAD, index or worktree.
    commit = git(repo, 'commit-tree', 'HEAD^{tree}', '-p', 'HEAD', '-m', 'upstream advance')
    git(repo, 'push', 'origin', commit + ':refs/heads/main')
    return commit


expected = {}
heads = {}
targets = {}


def register(repo, action):
    expected[repo.name] = action
    heads[repo.name] = git(repo, 'rev-parse', 'HEAD')


r = fixture('clean-behind')
targets[r.name] = advance(r)
register(r, 'pulled 1')
r = fixture('repo with spaces')
targets[r.name] = advance(r)
register(r, 'pulled 1')
r = fixture('up-to-date')
register(r, '-')

r = fixture('hidden-untracked')
git(r, 'config', 'status.showUntrackedFiles', 'no')
(r / 'untracked').write_text('must survive\n')
assert git(r, 'status', '--porcelain') == ''
advance(r)
register(r, 'skip: not clean')

for name, staged in [('unstaged', False), ('staged', True)]:
    r = fixture(name)
    (r / 'tracked').write_text('local change\n')
    if staged:
        git(r, 'add', 'tracked')
    advance(r)
    register(r, 'skip: not clean')

r = fixture('hidden-dirty-submodule')
sub = ROOT / 'sub-source'
sub.mkdir()
git(sub, 'init', '--initial-branch=main')
(sub / 'file').write_text('original\n')
git(sub, 'add', '.')
git(sub, 'commit', '-m', 'submodule base')
git(r, '-c', 'protocol.file.allow=always', 'submodule', 'add', str(sub), 'sub')
git(r, 'commit', '-am', 'add submodule')
git(r, 'push')
git(r, 'config', 'submodule.sub.ignore', 'all')
(r / 'sub' / 'file').write_text('dirty submodule\n')
assert git(r, 'status', '--porcelain') == ''
advance(r)
register(r, 'skip: not clean')

r = fixture('paused-sequencer')
base = git(r, 'rev-parse', 'HEAD')
git(r, 'checkout', '-b', 'topic')
(r / 'tracked').write_text('topic change\n')
git(r, 'commit', '-am', 'topic one')
first = git(r, 'rev-parse', 'HEAD')
(r / 'second').write_text('second topic commit\n')
git(r, 'add', '.')
git(r, 'commit', '-m', 'topic two')
second = git(r, 'rev-parse', 'HEAD')
git(r, 'checkout', 'main')
(r / 'tracked').write_text('main conflicting change\n')
git(r, 'commit', '-am', 'main conflict')
result = git(r, 'cherry-pick', first, second, ok=False)
assert result.returncode != 0
(r / 'tracked').write_text('resolved manually\n')
git(r, 'add', 'tracked')
git(r, 'commit', '--no-edit')
assert (r / '.git' / 'sequencer').is_dir()
assert not (r / '.git' / 'CHERRY_PICK_HEAD').exists()
assert not (r / '.git' / 'REVERT_HEAD').exists()
assert git(r, 'status', '--porcelain') == ''
advance(r)
register(r, 'skip: not clean')

r = fixture('no-origin')
git(r, 'remote', 'remove', 'origin')
register(r, 'skip: no origin')
r = fixture('no-upstream')
git(r, 'branch', '--unset-upstream')
advance(r)
register(r, 'skip: no upstream')
r = fixture('feature-branch')
git(r, 'checkout', '-b', 'feature')
advance(r)
register(r, 'skip: non-default branch')
r = fixture('detached')
git(r, 'checkout', '--detach')
advance(r)
register(r, 'skip: detached')
r = fixture('diverged')
advance(r)
git(r, 'commit', '--allow-empty', '-m', 'local divergent commit')
register(r, 'skip: diverged')
r = fixture('ahead-only')
git(r, 'commit', '--allow-empty', '-m', 'local ahead commit')
register(r, '-')
r = fixture('fetch-failed')
git(r, 'remote', 'set-url', 'origin', str(ROOT / 'nonexistent.git'))
register(r, 'FETCH FAILED')
r = fixture('unknown-default')
advance(r)
git(ROOT / 'unknown-default.git', 'symbolic-ref', 'HEAD', 'refs/heads/missing')
register(r, 'skip: default unknown')
r = fixture('wrong-upstream')
git(r, 'push', 'origin', 'HEAD:other')
git(r, 'fetch', 'origin')
git(r, 'branch', '--set-upstream-to=origin/other')
advance(r)
register(r, 'skip: upstream origin/other')

r = fixture('dirty-up-to-date')
(r / 'tracked').write_text('local change\n')
register(r, 'skip: not clean')

r = fixture('operation-up-to-date')
(r / '.git' / 'sequencer').mkdir()
register(r, 'skip: not clean')

r = fixture('ignored-collision')
(r / '.git' / 'info' / 'exclude').write_text('local-secret\n')
(r / 'local-secret').write_text('upstream contents\n')
git(r, 'add', '-f', 'local-secret')
tree = git(r, 'write-tree')
commit = git(r, 'commit-tree', tree, '-p', 'HEAD', '-m', 'track previously ignored file')
git(r, 'reset', 'HEAD', '--', 'local-secret')
(r / 'local-secret').write_text('local contents must survive\n')
git(r, 'push', 'origin', commit + ':refs/heads/main')
register(r, 'PULL FAILED')

# Reject invalid arguments before any fetch or merge can happen.
for args in [('--dryrun', str(REPOS)), (str(REPOS), str(REPOS))]:
    result = subprocess.run(['bash', SCRIPT, *args], env=ENV, text=True, capture_output=True)
    assert result.returncode == 2, (args, result)
    assert not result.stdout, result.stdout
    for name, head in heads.items():
        assert git(REPOS / name, 'rev-parse', 'HEAD') == head

# An explicit option terminator allows directory names beginning with a dash.
dash_root = ROOT / '-repos'
dash_root.mkdir()
result = subprocess.run(['bash', SCRIPT, '--', '-repos'], cwd=ROOT,
                        env=ENV, text=True, capture_output=True)
assert result.returncode == 0, result.stderr
assert 'No git repos found' in result.stdout

# Record all tracked/untracked working files and index bytes, including submodules.
def snapshot(repo):
    files = {}
    for path in repo.rglob('*'):
        if '.git' in path.relative_to(repo).parts or not path.is_file():
            continue
        files[str(path.relative_to(repo))] = path.read_bytes()
    return files, (repo / '.git' / 'index').read_bytes()

before = {name: snapshot(REPOS / name) for name in expected}
sequencer_before = {p.name: p.read_bytes() for p in (REPOS / 'paused-sequencer' / '.git' / 'sequencer').iterdir() if p.is_file()}


def run(dry):
    result = subprocess.run(['bash', SCRIPT, *(['--dry-run'] if dry else []), str(REPOS)],
                            env=ENV, text=True, capture_output=True, timeout=90)
    assert result.returncode == 0, result.stderr
    print('\n' + ('DRY RUN' if dry else 'LIVE RUN') + '\n' + result.stdout)
    rows = {}
    for line in result.stdout.splitlines()[1:]:
        if not line.strip():
            break
        cols = re.split(r'\s{2,}', line.strip())
        assert len(cols) == 7, repr(cols)
        rows[cols[0]] = cols
    assert set(rows) == set(expected)
    for name, action in expected.items():
        desired = action.replace('pulled ', 'would pull ') if dry else action
        if dry and name == 'ignored-collision':
            desired = 'would pull 1'
        assert rows[name][-1] == desired, (name, rows[name], desired)
        head = git(REPOS / name, 'rev-parse', 'HEAD')
        assert head == (targets[name] if not dry and name in targets else heads[name]), name
        # Git can refresh index stat caches; assert content/staging semantically instead.
        assert snapshot(REPOS / name)[0] == before[name][0], name
        assert git(REPOS / name, 'diff', '--cached', '--name-only') == ('tracked' if name == 'staged' else ''), name
    assert rows['hidden-untracked'][2].startswith('dirty(')
    assert rows['hidden-dirty-submodule'][2].startswith('dirty(')
    assert rows['paused-sequencer'][2] == 'clean,sequencer'
    assert rows['feature-branch'][5] == '+0/-1 main'
    assert rows['diverged'][4] == '+1/-1'
    seq = REPOS / 'paused-sequencer' / '.git' / 'sequencer'
    assert {p.name: p.read_bytes() for p in seq.iterdir() if p.is_file()} == sequencer_before
    print(f'PASS: {len(expected)} scenarios; HEADs, working files, staging and sequencer verified')


print('Fixtures retained at:', ROOT, flush=True)
run(True)
run(False)
# After a successful sync, a second live run should be a no-op for pulled repos.
for name in targets:
    expected[name] = '-'
    heads[name] = targets[name]
targets.clear()
run(False)
print(f'\nALL PASSED: {len(expected)} scenarios x 3 runs = {len(expected) * 3} scenario checks; argument validation passed')
