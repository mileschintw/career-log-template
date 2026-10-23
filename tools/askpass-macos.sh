#!/bin/sh
# SUDO_ASKPASS for tools/setup.sh on macOS (#151): sudo asks for the user's password through macOS's
# own dialog (osascript, built in), since the agent's shell cannot answer a terminal prompt. The
# password goes from the dialog to sudo and nowhere else. A cancel, or no answer within 10 minutes,
# exits nonzero, so sudo fails and setup goes on without the step.
exec /usr/bin/osascript \
  -e 'set r to display dialog "career-log setup is installing Homebrew, to install poppler (it checks resume PDFs). macOS needs your login password for this. It goes to macOS only." default answer "" with hidden answer with title "career-log setup" with icon caution giving up after 600' \
  -e 'if gave up of r then error number -128' \
  -e 'text returned of r'
