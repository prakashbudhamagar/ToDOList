import { useCallback, useEffect, useState } from 'react'

import { createTodo, deleteTodo, listTodos, updateTodo } from './api.js'
import { DEFAULT_PRIORITY } from './priorities.js'

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
    async (title, priority = DEFAULT_PRIORITY) => {
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
        setError(`Could not add the task: ${err.message}`)
        return false
      }
    },
    [loadTodos],
  )

  // `fields` holds only what changed - { title } and/or { priority }.
  const editTodo = useCallback(
    async (id, fields) => {
      const changes = { ...fields }
      if (changes.title !== undefined) {
        changes.title = changes.title.trim()
        if (!changes.title) {
          setError('A task needs a title.')
          return false
        }
      }
      try {
        await updateTodo(id, changes)
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

  return { todos, loading, error, addTodo, editTodo, removeTodo, reload: loadTodos }
<<<<<<< HEAD:frontend/src/features/todos/useTodos.js
}
=======
}
>>>>>>> 8c201bfeefa40177a9044714891cc0f7c9ec53f4:frontend/src/hooks/useTodos.js
