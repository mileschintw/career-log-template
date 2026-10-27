# Excerpts of perishable sources

Read this when a fact you are writing into an entry cites an agent session: the user's words in it, or a decision reached in it ([SKILL.md › Provenance](SKILL.md#rules-for-every-mode)). The transcript is perishable (Claude Code deletes it after about 30 days), so the passages the fact cites are copied into `sources/<agent>/<YYYY-MM-DD>-<slug>.md`, one file per session and topic (a forked session is a session of its own), and from then on the excerpt is the durable source the entry cites.

## Citing an excerpt

The user's words in this session are cited `(user, YYYY-MM-DD; <key> U<k>)` once excerpted, dated the day of the turn, and `(user, YYYY-MM-DD)` alone while no excerpt holds them. A turn first read from another session's transcript or from an imported chat is cited by its key alone: the user has not confirmed it in this session. A fact already tagged `(user, …)` keeps its tag when its key is added.

## The key's date

An excerpt's key is `<agent>-<YYYY-MM-DD>-<slug>`, its file's name. The tool dates it by the rules at the end of `<tool> --help` (`<tool>` below), so one session keeps one date in all its files, and its `- Key date:` line says which rule it used; a key without that line is read as written.

## Claude Code

`<tool>` is `python3 -I <root>/tools/chat_export.py` (`py -3 -I` on Windows).

1. **Find the transcript.** `<tool> turns` reads the newest transcript of the current directory, usually the session you are in: check that its `U<k>` lines are this session's user turns. For another session, pass `--cwd <the directory it ran in>` or the transcript's path. For the sessions behind quotes or session citations already in an entry, `<tool> find "<a few words of one sentence the user typed>" "<of another>" ...` prints each one's transcript and turn, searching the Log's own sessions first; give them all in one run. Done when you have the transcript path and the turns' labels, or `find` printed `not found` for the quote's phrase and the quote goes to [Other agents and lost transcripts](#other-agents-and-lost-transcripts).
2. **Choose the turns.** `U<k>` is the k-th turn the user typed; `A<k>` is the assistant's text after it. Keep the user turns the fact cites, whole. Keep an assistant turn only when a kept user turn cannot be understood without it, and then only its paragraphs that give the context (`A<k>:<n>-<m>`; `<tool> turns <transcript> --show <turns>` prints the turns with their paragraph numbers). Done when every kept turn is one a fact cites or one it needs for context.
3. **Write the excerpt.** `<tool> excerpt <transcript> --keep <turns> --slug <topic> --out <root>/sources`, with a slug naming the topic (`retry-queue-design`). A turn already in the file stays as it is, so choose an assistant turn's paragraphs once. Done when the tool has printed the key and each kept user turn's day, `(user, YYYY-MM-DD)`: a turn of this session is cited with that day, as Provenance says, and another session's by its key alone.
4. **Read the file.** The tool replaces the secrets it recognises with `[redacted: <kind>]` and prints a count. Read every kept turn for a credential, token or password it missed, and replace each one the same way by hand: that is the only edit an excerpt takes. Done when no kept turn holds a secret.
5. **Cite it** in the entry, as Provenance says, and commit the excerpt in the same commit as the line that cites it. Done when both are in one commit.

## Other agents and lost transcripts

An agent the tool does not read, or a quote whose transcript is already gone, gets its excerpt from `<tool> quote` (`<tool> --help` gives its arguments and the form of its `--turns` file). Yours are the choices: the turns to quote, the title, a slug the session's files do not have yet, and the `--note` paragraph saying where the turns came from (for a quote copied from an entry: the transcript is gone and the text is the entry's quote). Then read the file as step 4 says and cite it as step 5 says. Done when the tool has printed the key.

## Files

| Path | What |
|---|---|
| `sources/<agent>/<YYYY-MM-DD>-<slug>.md` | Excerpts of agent sessions (`claude-code/`, ...), one session per file: the turns entries cite, added to by the tool, the only hand edit a redaction ([excerpts.md](excerpts.md)) |
