import { useState } from 'react'

/**
 * One task row. Editing and the delete confirmation are local UI state, so the
 * parent only has to provide the API actions.
 */
export default function TodoItem({ todo, onUpdate, onDelete }) {
  const [editing, setEditing] = useState(false)
  const [editedTitle, setEditedTitle] = useState(todo.title)
  const [confirmingDelete, setConfirmingDelete] = useState(false)

  function startEditing() {
    setEditedTitle(todo.title)
    setConfirmingDelete(false)
    setEditing(true)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (await onUpdate(todo.id, editedTitle)) {
      setEditing(false)
    }
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
