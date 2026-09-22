export type PriorityValue = 1 | 2 | 3

export interface Todo {
  id: number
  title: string
  priority: PriorityValue
  priority_label: string
  create_at: string
}

export interface TodoChanges {
  title?: string
  priority?: PriorityValue
}
