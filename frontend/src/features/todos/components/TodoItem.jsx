import { useState } from 'react'

import PrioritySelect from './PrioritySelect.jsx'

/**
 * One task row. Editing, the priority change and the delete confirmation are
 * local UI state, so the parent only has to provide the API actions.
 */
export default function TodoItem({ todo, onUpdate, onDelete }) {
  const [editing, setEditing] = useState(false)
  const [editedTitle, setEditedTitle] = useState(todo.title)
  const [editedPriority, setEditedPriority] = useState(todo.priority)
  const [confirmingDelete, setConfirmingDelete] = useState(false)

  function startEditing() {
    setEditedTitle(todo.title)
    setEditedPriority(todo.priority)
    setConfirmingDelete(false)
    setEditing(true)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (await onUpdate(todo.id, { title: editedTitle, priority: editedPriority })) {
      setEditing(false)
    }
  }

  /** Changing the level in the row saves it right away, no edit mode needed. */
  async function handlePriorityChange(priority) {
    await onUpdate(todo.id, { priority })
  }

  async function handleDelete() {
    if (await onDelete(todo.id)) {
      setConfirmingDelete(false)
    }
  }

  if (editing) {
    return (
      <li>
        <form className="edit-form" onSubmit={handleSubmit}>
          <input
            type="text"
            value={editedTitle}
            maxLength={100}
            autoFocus
            aria-label="Task title"
            onChange={(event) => setEditedTitle(event.target.value)}
          />
          <PrioritySelect value={editedPriority} onChange={setEditedPriority} />
          <button type="submit">Save</button>
          <button type="button" className="secondary" onClick={() => setEditing(false)}>
            Cancel
          </button>
        </form>
      </li>
    )
  }

  const created = new Date(todo.create_at)

  return (
    <li>
      <span className="title">{todo.title}</span>
      <PrioritySelect value={todo.priority} onChange={handlePriorityChange} />
      <span className="meta">
        <time dateTime={created.toISOString()}>{created.toLocaleString()}</time>
        {confirmingDelete ? (
          <>
            <span className="confirm">Delete this task?</span>
            <button type="button" className="danger" onClick={handleDelete}>
              Yes, Delete
            </button>
            <button
              type="button"
              className="secondary"
              onClick={() => setConfirmingDelete(false)}
            >
              Cancel
            </button>
          </>
        ) : (
          <>
            <button type="button" className="secondary" onClick={startEditing}>
              Edit
            </button>
            <button
              type="button"
              className="danger"
              onClick={() => setConfirmingDelete(true)}
            >
              Delete
            </button>
          </>
        )}
      </span>
    </li>
  )
}