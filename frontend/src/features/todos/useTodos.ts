import { useCallback, useEffect, useState } from 'react'

import { errorMessage } from '../../shared/api/client'
import { createTodo, deleteTodo, listTodos, updateTodo } from './api'
import { DEFAULT_PRIORITY } from './priorities'
import type { PriorityValue, Todo, TodoChanges } from './types'

export interface UseTodosResult {
  todos: Todo[]
  loading: boolean
  error: string | null
  addTodo: (title: string, priority?: PriorityValue) => Promise<boolean>
  editTodo: (id: number, fields: TodoChanges) => Promise<boolean>
  removeTodo: (id: number) => Promise<boolean>
  reload: () => Promise<void>
}

export function useTodos(): UseTodosResult {
  const [todos, setTodos] = useState<Todo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadTodos = useCallback(async () => {
    try {
      setTodos(await listTodos())
      setError(null)
    } catch (err) {
      setError(`Could not load tasks: ${errorMessage(err)}`)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadTodos()
  }, [loadTodos])

  const addTodo = useCallback(
    async (title: string, priority: PriorityValue = DEFAULT_PRIORITY) => {
      const trimmed = title.trim()
      if (!trimmed) {
        return false
      }
      try {
        await createTodo(trimmed, priority)
        setError(null)
        await loadTodos()
        return true
      } catch (err) {
        setError(`Could not add the task: ${errorMessage(err)}`)
        return false
      }
    },
    [loadTodos],
  )

  const editTodo = useCallback(
    async (id: number, fields: TodoChanges) => {
      const changes: TodoChanges = { ...fields }
      if (changes.title !== undefined) {
        const title = changes.title.trim()
        if (!title) {
          setError('A task needs a title.')
          return false
        }
        changes.title = title
      }
      try {
        await updateTodo(id, changes)
        setError(null)
        await loadTodos()
        return true
      } catch (err) {
        setError(`Could not update the task: ${errorMessage(err)}`)
        return false
      }
    },
    [loadTodos],
  )

  const removeTodo = useCallback(
    async (id: number) => {
      try {
        await deleteTodo(id)
        setError(null)
        await loadTodos()
        return true
      } catch (err) {
        setError(`Could not delete the task: ${errorMessage(err)}`)
        return false
      }
    },
    [loadTodos],
  )

  return { todos, loading, error, addTodo, editTodo, removeTodo, reload: loadTodos }
}
