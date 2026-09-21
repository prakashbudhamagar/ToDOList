import TodoItem from './TodoItem.jsx'

/** Renders the task rows, the loading state and the empty state. */
export default function TodoList({ todos, loading, onUpdate, onDelete }) {
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