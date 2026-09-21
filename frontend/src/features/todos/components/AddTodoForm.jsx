import { useState } from 'react'

import { DEFAULT_PRIORITY } from '../priorities.js'
import PrioritySelect from './PrioritySelect.jsx'

/** Form that creates a task; clears itself once the API call succeeded. */
export default function AddTodoForm({ onAdd }) {
  const [title, setTitle] = useState('')
  const [priority, setPriority] = useState(DEFAULT_PRIORITY)

  async function handleSubmit(event) {
    event.preventDefault()
    if (await onAdd(title, priority)) {
      setTitle('')
      setPriority(DEFAULT_PRIORITY)
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
      <PrioritySelect value={priority} onChange={setPriority} />
      <button type="submit">Add Task</button>
    </form>
  )
}