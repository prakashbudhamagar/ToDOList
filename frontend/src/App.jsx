import AddTodoForm from './components/AddTodoForm.jsx'
import ChatPanel from './components/ChatPanel.jsx'
import TodoList from './components/TodoList.jsx'
import { useTodos } from './hooks/useTodos.js'

/** Page shell: wires the task state from useTodos to the presentational parts. */
export default function App() {
  const { todos, loading, error, addTodo, editTodo, removeTodo, reload } = useTodos()

  return (
    <main className="app">
      <h1>Prkash to Do</h1>

      <AddTodoForm onAdd={addTodo} />

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      <TodoList todos={todos} loading={loading} onUpdate={editTodo} onDelete={removeTodo} />

      <ChatPanel onTasksChanged={reload} />
    </main>
  )
}
