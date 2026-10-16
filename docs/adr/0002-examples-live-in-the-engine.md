# Examples live in the Engine, never in the Log

The fictional Example (an entry, a resume `.tex`, a filled profile and direction) sits under `skills/career-log/examples/`, not under `entries/` or in the `README.md` index. The modes read every entry and index row as the user's own facts (`write`, `audit`, `import`), so an Example inside the Log would end up on a real resume. Keeping it in the Engine means the Template's Log starts empty, while the format and the setup check still have something to point at.
