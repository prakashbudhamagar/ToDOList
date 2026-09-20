import { useState } from 'react'

/** Form that creates a task; clears itself once the API call succeeded. */
export default function AddTodoForm({ onAdd }) {
  const [title, setTitle] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    if (await onAdd(title)) {
      setTitle('')
    }
  }

  return (
    <form className="add-form" onSubmit={handleSubmit}>
      <input
        type="text"
        value={title}
        maxLength={100}
        placeholder="What needs to be done?"
        onChange={(event) => setTitle(event.target.value)}
      />
      <button type="submit">Add Task</button>
    </form>
  )
}
