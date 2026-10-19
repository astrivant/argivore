// Verify contributor messages and tag admission without contacting GitHub.
const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const feedback = require('./feedback.cjs');

function fixture(t) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'argivore-feedback-'));
  const previous = { ...process.env };
  process.env.RUNNER_TEMP = directory;
  process.env.RELEASE_TAG = 'v1.2.3';
  process.env.SOURCE_SHA = 'a'.repeat(40);
  const calls = [];
  const rest = {
    git: {
      getRef: async () => ({ data: { object: { type: 'tag', sha: 'b'.repeat(40) } } }),
      getTag: async () => ({ data: { verification: { verified: true }, object: { type: 'commit', sha: process.env.SOURCE_SHA } } }),
    },
    repos: {
      getReleaseByTag: async () => ({ data: { draft: false, html_url: 'https://example.test/release' } }),
      listReleases: async () => [],
      listPullRequestsAssociatedWithCommit: async () => [],
      generateReleaseNotes: async () => ({ data: { body: 'Existing generated summary' } }),
    },
    issues: { listComments: async () => [], createComment: async (args) => calls.push(args) },
  };
  fs.writeFileSync(path.join(directory, 'release-prs.json'), JSON.stringify([{ number: 7, author: 'contributor' }]));
  t.after(() => {
    process.env = previous;
    fs.rmSync(directory, { recursive: true, force: true });
  });
  return { directory, calls, rest, args: { github: { rest, paginate: (method, args) => method(args) }, context: { repo: { owner: 'example', repo: 'project' } }, core: { info() {} } } };
}

test('notify once with contributor and immutable version, preserving prior comments', async (t) => {
  const f = fixture(t);
  process.env.RELEASE_OPERATION = 'notify';
  await feedback(f.args);
  assert.equal(f.calls.length, 1);
  assert.match(f.calls[0].body, /@contributor/);
  assert.match(f.calls[0].body, /v1\.2\.3/);
  f.rest.issues.listComments = async () => [{ body: f.calls[0].body }];
  await feedback(f.args);
  assert.equal(f.calls.length, 1);
});

test('draft release cannot notify contributors', async (t) => {
  const f = fixture(t);
  process.env.RELEASE_OPERATION = 'notify';
  f.rest.repos.getReleaseByTag = async () => ({ data: { draft: true } });
  await assert.rejects(feedback(f.args), /published release/);
  assert.equal(f.calls.length, 0);
});

for (const invalid of ['lightweight', 'unverified', 'wrong-source']) {
  test(`prepare rejects ${invalid} tag before producing release notes`, async (t) => {
    const f = fixture(t);
    process.env.RELEASE_OPERATION = 'prepare';
    if (invalid === 'lightweight') f.rest.git.getRef = async () => ({ data: { object: { type: 'commit' } } });
    else f.rest.git.getTag = async () => ({ data: { verification: { verified: invalid !== 'unverified' }, object: { type: 'commit', sha: 'c'.repeat(40) } } });
    await assert.rejects(feedback(f.args), /tag|Tag/);
    assert.equal(fs.existsSync(path.join(f.directory, 'release-notes.md')), false);
  });
}

test('notes classify included merges once and retain external contributor credit', async (t) => {
  const f = fixture(t);
  const previousCwd = process.cwd();
  t.after(() => process.chdir(previousCwd));
  execFileSync('git', ['init', '--quiet', f.directory]);
  process.chdir(f.directory);
  execFileSync('git', ['-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test', '-c', 'commit.gpgsign=false', 'commit', '--quiet', '--allow-empty', '-m', 'fixture']);
  const sha = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
  process.env.SOURCE_SHA = sha;
  process.env.RELEASE_OPERATION = 'prepare';
  f.rest.repos.listPullRequestsAssociatedWithCommit = async () => [
    { number: 7, merged_at: '2026-01-01', merge_commit_sha: sha, base: { repo: { full_name: 'example/project' } }, user: { login: 'emmeowzing' }, title: 'Repair validation', html_url: 'https://example.test/7', labels: [{ name: 'bug' }] },
    { number: 8, merged_at: '2026-01-01', merge_commit_sha: 'd'.repeat(40), base: { repo: { full_name: 'example/project' } } },
  ];
  f.rest.repos.generateReleaseNotes = async () => ({ data: { body: "## What's Changed\n* Duplicate change for #7\n\n## New Contributors\n* @Emmeowzing made their first contribution in #1\n* @example made their first contribution in #2\n* @contributor made their first contribution in #7\n\n**Full Changelog**: https://example.test/changelog" } });
  await feedback(f.args);
  const notes = fs.readFileSync(path.join(f.directory, 'release-notes.md'), 'utf8');
  assert.match(notes, /### Fixes/);
  assert.match(notes, /Repair validation/);
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(f.directory, 'release-prs.json'), 'utf8')).map((pr) => pr.author), ['emmeowzing']);
  assert.equal((notes.match(/^## What changed$/gm) || []).length, 1);
  assert.doesNotMatch(notes, /What's Changed|GitHub release summary|Duplicate change|@Emmeowzing|@example/);
  assert.match(notes, /## New Contributors\n\n\* @contributor/);
  assert.match(notes, /Full Changelog.*https:\/\/github.com\/example\/project\/commits\/v1.2.3/);
  assert.match(notes, /Artifact verification/);
  assert.doesNotMatch(notes, /#8/);
  assert.equal(f.calls.length, 0);
});


test('maintainer-only contributor sections disappear without changing similar account names', () => {
  const body = '## New Contributors\r\n* @Owner made their first contribution in #1\r\n\r\n**Full Changelog**: https://example.test';
  assert.equal(feedback.newContributors(body, ['owner']), '');
  assert.match(feedback.newContributors(body.replace('@Owner ', '@Owner-extra '), ['owner']), /@Owner-extra/);
  assert.equal(feedback.newContributors('## What\'s Changed\n* A fix', ['owner']), '');
});

test('contributor filtering stops at the next heading and preserves unrecognized attribution text', () => {
  const body = '## New Contributors\n* An unusual attribution\n\n## Other section\n* unrelated';
  assert.equal(feedback.newContributors(body, []), '## New Contributors\n\n* An unusual attribution');
});
