"""Rough effort estimates for tasks, used by the assistant's recommendations.

Nobody can know how long a task really takes, so a title is turned into a
plausible duration from two cheap signals: how much the title says (more words
usually mean more scope) and a few verbs that are reliably quick or reliably
slow. The assistant always presents the result as an estimate, never as a fact.
"""

BASE_MINUTES = 15        # a one-word errand
MINUTES_PER_WORD = 10    # every extra word hints at more scope
QUICK_TASK_MINUTES = 15  # ceiling for chores that are a single action
DEEP_TASK_MINUTES = 60   # floor for tasks that need thinking or writing
MAX_MINUTES = 240        # nothing on a todo list gets booked for half a day

# Chores that are usually one action, however long the title is.
QUICK_HINTS = ('call', 'email', 'ping', 'reply', 'text', 'confirm', 'book', 'buy')
# Verbs that need real work, so they rarely fit in a coffee break.
DEEP_HINTS = (
    'write', 'review', 'design', 'plan', 'research', 'prepare', 'refactor',
    'migrate', 'implement', 'build', 'draft', 'report', 'investigate',
)


def estimate_minutes(title):
    """Return a plausible number of minutes the titled task may take."""
    lowered = str(title or '').lower()
    minutes = BASE_MINUTES + MINUTES_PER_WORD * max(len(lowered.split()) - 1, 0)

    if any(hint in lowered for hint in QUICK_HINTS):
        minutes = min(minutes, QUICK_TASK_MINUTES)
    if any(hint in lowered for hint in DEEP_HINTS):
        minutes = max(minutes, DEEP_TASK_MINUTES)

    return min(minutes, MAX_MINUTES)


def format_minutes(minutes):
    """Render minutes the way the assistant should say them, e.g. '~1 h 30 min'."""
    if minutes < 60:
        return f'~{minutes} min'
    hours, rest = divmod(minutes, 60)
    if not rest:
        return f'~{hours} h'
    return f'~{hours} h {rest} min'
