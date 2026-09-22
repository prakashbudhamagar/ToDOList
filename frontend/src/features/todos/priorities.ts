import type { PriorityValue } from './types'

export interface PriorityOption {
  value: PriorityValue
  label: string
}

export const PRIORITY_OPTIONS: readonly PriorityOption[] = [
  { value: 3, label: 'High' },
  { value: 2, label: 'Medium' },
  { value: 1, label: 'Low' },
]

export const DEFAULT_PRIORITY: PriorityValue = 2

export function prioritySlug(value: PriorityValue): string {
  const option = PRIORITY_OPTIONS.find((entry) => entry.value === value)
  return (option?.label ?? 'Medium').toLowerCase()
}
