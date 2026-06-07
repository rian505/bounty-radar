# Publishing `bounty-radar` to PyPI

Everything is wired so you publish with **zero secrets stored** — PyPI's
Trusted Publishing (OIDC) lets GitHub Actions authenticate to PyPI directly.
You never paste an API token into GitHub.

Do this once, then every GitHub Release auto-publishes.

---

## One-time setup (~5 minutes, all in your browser)

### 1. Create a PyPI account
- Go to https://pypi.org/account/register/ and sign up (verify your email).
- Enable 2FA when prompted (PyPI requires it for publishing).

### 2. Register the project name + Trusted Publisher

Because the package isn't on PyPI yet, use the **pending publisher** flow:

- Go to https://pypi.org/manage/account/publishing/
- Under **Add a new pending publisher**, fill in:
  - **PyPI Project Name:** `bounty-radar`
  - **Owner:** `rian505`
  - **Repository name:** `bounty-radar`
  - **Workflow name:** `publish.yml`
  - **Environment name:** `pypi`
- Click **Add**.

That tells PyPI: "trust the `publish.yml` workflow in `rian505/bounty-radar`
(running in the `pypi` environment) to publish this package." No token needed.

### 3. Create the `pypi` environment on GitHub
- Repo → **Settings → Environments → New environment** → name it `pypi`.
- (Optional but recommended) add yourself as a required reviewer so a release
  can't publish without your click.

---

## Publishing a release

When you're ready to ship a version:

1. Bump the version in **two** places (keep them in sync):
   - `pyproject.toml` → `version = "0.1.1"`
   - `bounty_radar/__init__.py` → `__version__ = "0.1.1"`
2. Commit and push.
3. On GitHub: **Releases → Draft a new release**.
   - Tag: `v0.1.1` (create on publish)
   - Title + notes: whatever you want.
   - **Publish release.**
4. The `publish.yml` workflow runs automatically: it tests on Python 3.9/3.11/3.12,
   builds, validates with `twine check`, then publishes to PyPI.
5. A minute later: `pip install bounty-radar` works for anyone, anywhere.

You can also trigger it manually from **Actions → Publish to PyPI → Run workflow**
(only useful after the first real release exists).

---

## Verifying it worked

```bash
pip install bounty-radar
bounty-radar --version      # -> bounty-radar 0.1.1
```

And the project page appears at https://pypi.org/project/bounty-radar/

---

## Build locally (optional sanity check)

```bash
pip install build twine
python -m build
twine check dist/*
```

Both artifacts (`.tar.gz` + `.whl`) should report `PASSED` — verified working
on this codebase.

---

## Troubleshooting

- **"Trusted publishing exchange failure"** — the publisher config on PyPI
  (step 2) must match *exactly*: owner `rian505`, repo `bounty-radar`,
  workflow `publish.yml`, environment `pypi`. A typo in any field fails the OIDC exchange.
- **"Project already exists / name taken"** — `bounty-radar` may be claimed.
  Pick a new name in `pyproject.toml` (`name = "..."`) and redo step 2 with it.
- **Tests fail in CI but pass locally** — CI runs on 3.9/3.11/3.12; check the
  matrix logs in the Actions tab for the version that broke.
