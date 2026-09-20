import { useCallback, useEffect, useState } from 'react'

import { createTodo, deleteTodo, listTodos, updateTodo } from '../api/todos.js'

export function useTodos() {
  const [todos, setTodos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadTodos = useCallback(async () => {
    try {
      setTodos(await listTodos())
      setError(null)
    } catch (err) {
      setError(`Could not load tasks: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadTodos()
  }, [loadTodos])

  const addTodo = useCallback(
    async (title) => {
      const trimmed = title.trim()
      if (!trimmed) {
        return false
      }
      try {
        await createTodo(trimmed)
        setError(null)
        await loadTodos()
        return true
      } catch (err) {
        setError(`Could not add the task: ${err.message}`)
        return false
      }
    },
    [loadTodos],
  )

  const editTodo = useCallback(
    async (id, title) => {
      const trimmed = title.trim()
      if (!trimmed) {
        setError('A task needs a title.')
        return false
      }
      try {
        await updateTodo(id, trimmed)
        setError(null)
        await loadTodos()
        return true
      } catch (err) {
        setError(`Could not update the task: ${err.message}`)
        return false
      }
    },
    [loadTodos],
  )

  const removeTodo = useCallback(
    async (id) => {
      try {
        await deleteTodo(id)
        setError(null)
        await loadTodos()
        return true
      } catch (err) {
        setError(`Could not delete the task: ${err.message}`)
        return false
      }
    },
    [loadTodos],
  )

  return { todos, loading, error, addTodo, editTodo, removeTodo }
}
