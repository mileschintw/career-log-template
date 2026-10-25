# Sent versions

Every resume an employer received must be recoverable exactly as sent. `<root>` is the Log's root, as [SKILL.md](SKILL.md) resolves it; `<app>` is `python3 -I <root>/tools/application.py`, with `--root <root>` after its arguments.

- **Through an application:** its folder in `outputs/applications/` keeps the `.tex` and `.pdf`, and is not edited after sending.
- **Outside one** (a career fair, a recruiter email): record the commit, not a copy. `<app> sent <target>` prints the `cell:` to write in the `applications.md` row, for a version sent just now; for one sent earlier, add `--before "<when it was sent>"`.
- **Through the user's own application tool** (`direction.md › Tools the user already uses`): no row, since the tool already records each application. The user keeps the target's file name (`<target>.pdf`) when uploading, so the tool shows which version went. To recover it, take the application's date and time from the tool: `<app> sent <target> --before "<YYYY-MM-DD HH:MM>"` prints its `version:`. When the tool shows only a date, give the date alone; then a `changed that day:` count above 0 means asking the user which version went.
- The hash is the source of truth; the link is a convenience. To read the sent version: `<app> sent-show "<the row's cell>"` (`--out <file>` writes it there); a row that gives only a hash needs `--target <target>`.
