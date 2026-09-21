<<<<<<< HEAD
import { AddTodoForm, TodoList, useTodos } from './features/todos'
import { ChatPanel } from './features/chat'
=======
import AddTodoForm from './components/AddTodoForm.jsx'
import ChatPanel from './components/ChatPanel.jsx'
import TodoList from './components/TodoList.jsx'
import { useTodos } from './hooks/useTodos.js'
>>>>>>> 8c201bfeefa40177a9044714891cc0f7c9ec53f4

/** Page shell: wires the task state from useTodos to the presentational parts. */
export default function App() {
  const { todos, loading, error, addTodo, editTodo, removeTodo, reload } = useTodos()

  return (
    <main className="app">
<<<<<<< HEAD
      <h1>My Task</h1>
=======
      <h1>Prkash to Do</h1>
>>>>>>> 8c201bfeefa40177a9044714891cc0f7c9ec53f4

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