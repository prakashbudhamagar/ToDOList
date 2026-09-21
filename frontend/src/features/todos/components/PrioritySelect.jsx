import { PRIORITY_OPTIONS, prioritySlug } from '../priorities.js'

/**
 * Priority dropdown, tinted by the selected level (see index.css). Shared by the
 * add form and every task row so the three levels always render the same way.
 */
export default function PrioritySelect({ value, onChange, label = 'Priority', disabled = false }) {
  return (
    <select
      className={`priority-select priority-${prioritySlug(value)}`}
      value={value}
      aria-label={label}
      disabled={disabled}
      onChange={(event) => onChange(Number(event.target.value))}
    >
      {PRIORITY_OPTIONS.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  )
}
