import AddTodoForm from './components/AddTodoForm.jsx'
import TodoList from './components/TodoList.jsx'
import { useTodos } from './hooks/useTodos.js'

/** Page shell: wires the task state from useTodos to the presentational parts. */
export default function App() {
  const { todos, loading, error, addTodo, editTodo, removeTodo } = useTodos()

  return (
    <main className="app">
      <h1>Ty Task</h1>

      <AddTodoForm onAdd={addTodo} />

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      <TodoList todos={todos} loading={loading} onUpdate={editTodo} onDelete={removeTodo} />
    </main>
  )
}
