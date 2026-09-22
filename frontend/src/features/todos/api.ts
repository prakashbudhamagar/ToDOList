import { request } from '../../shared/api/client'
import type { PriorityValue, Todo, TodoChanges } from './types'

export const listTodos = (): Promise<Todo[]> => request<Todo[]>('/todos/')

export const createTodo = (title: string, priority: PriorityValue): Promise<Todo> =>
  request<Todo>('/todos/', { method: 'POST', body: JSON.stringify({ title, priority }) })

export const updateTodo = (id: number, fields: TodoChanges): Promise<Todo> =>
  request<Todo>(`/todos/${id}/`, { method: 'PATCH', body: JSON.stringify(fields) })

export const deleteTodo = (id: number): Promise<null> =>
  request<null>(`/todos/${id}/`, { method: 'DELETE' })
