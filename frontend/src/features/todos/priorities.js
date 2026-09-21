/**
 * The three priority levels, mirroring `Todo.Priority` in the backend
 * (backend/tasks/models.py). A higher number is more urgent, medium is the
 * default, and the API stores the number while showing a label for it.
 */
export const PRIORITY_OPTIONS = [
  { value: 3, label: 'High' },
  { value: 2, label: 'Medium' },
  { value: 1, label: 'Low' },
]

export const DEFAULT_PRIORITY = 2

/** CSS suffix that colours a priority, e.g. 'high' for index.css. */
export function prioritySlug(value) {
  const option = PRIORITY_OPTIONS.find((entry) => entry.value === value)
  return (option?.label ?? 'Medium').toLowerCase()
}
