import { ChatPanel } from './features/chat'
import { AddTodoForm, TodoList, useTodos } from './features/todos'

import './App.scss'

export default function App() {
  const { todos, loading, error, addTodo, editTodo, removeTodo, reload } = useTodos()

  return (
    <main className="app">
      <h1>Prakash To Do</h1>

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
