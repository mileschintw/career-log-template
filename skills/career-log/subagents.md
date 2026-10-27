# Subagents

How to write a subagent's prompt, check its reply, and give each one that writes files its own folder. The agent type and the model its call sets are in [SKILL.md › Subagents](SKILL.md#rules-for-every-mode).

## The prompt

A subagent starts with none of this session's context and has not read SKILL.md. Its prompt's first line points it at the section it follows (`Read <root>/skills/career-log/<file> whole and follow its <step or heading>`, with `<root>` replaced by the Log's absolute path); the rest of the prompt is only the data that section needs and this session alone knows (the user's answers, paths, names), never a copy of the section's instructions. Where a mode gives the prompt itself, use that prompt as the mode says.

## The reply

Check what each subagent returns against the section before using it.

## Subagent files

Subagents started together share this checkout and the agent's scratch space, so give each one that writes files a folder of its own, outside every folder its section writes: end its prompt, a mode's included, with the line `Create <folder> and put there every file you make that your instructions and the files they point to do not name (scripts, notes, page text), in place of your scratchpad.`, `<folder>` an absolute path named after what that subagent alone handles (its batch, its posting). It goes under the run's working folder when the mode has one, and goes with it; else it is `<root>/.build/tmp/<mode>-<HHMMSS>-<n>/` (the time you start them, `<n>` its number from 1), which you delete once they have all replied.
