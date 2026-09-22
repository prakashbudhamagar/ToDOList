import type { Todo, TodoChanges } from '../types'
import TodoItem from './TodoItem'

import './TodoList.scss'

export interface TodoListProps {
  todos: Todo[]
  loading: boolean
  onUpdate: (id: number, fields: TodoChanges) => Promise<boolean>
  onDelete: (id: number) => Promise<boolean>
}

export default function TodoList({ todos, loading, onUpdate, onDelete }: TodoListProps) {
  if (loading) {
    return <p className="empty">Loading...</p>
  }

  return (
    <ul className="todo-list">
      {todos.map((todo) => (
        <TodoItem key={todo.id} todo={todo} onUpdate={onUpdate} onDelete={onDelete} />
      ))}
      {todos.length === 0 && <li className="empty">No Task Yet</li>}
    </ul>
  )
}
