# Browser capture uses playwright-cli, installed when first needed

Browser capture used the browser pane built into one agent's desktop app: other agents have no such tool, and its results came back through the tool call, so a large capture had to be sliced and reassembled and could lose characters. It now uses Playwright's agent CLI (`playwright-cli`) with the skill that CLI installs, which any agent with a shell can run and which writes captures straight to files; site recipes stay in the modes. It is optional, because most Logs never need it: the agent checks for it the first time a Browser capture comes up in a session and, on the user's yes, installs Node, the CLI, its skill and, where Chrome is missing, a browser itself, handing the user any command that needs an administrator password. The installed skill is not committed: it is third-party text tied to the installed CLI's version, so a committed copy would drift from what each machine runs and would ship in the Template. Sign-ins live in one browser profile per machine, at a fixed path outside the repo, so nothing from them can be committed and every clone and worktree shares them; the CLI's own `--persistent` profile is not used, because it keeps a separate profile per folder.

## Considered options

- **Our own capture script in `tools/`**: deterministic, but covers only the sites we write recipes for; the CLI and its skill let the agent read a new source without one.
- **Playwright MCP**: each agent loads MCP servers its own way, so it would not be any more portable than the browser pane.
- **Keep the built-in browser**: kept only as a fallback, after the CLI, for a user who declines the install or a machine where the CLI cannot run.
