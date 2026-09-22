import { useState } from 'react'
import type { FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from "@/components/ui/input"
import { DEFAULT_PRIORITY } from '../priorities'
import type { PriorityValue } from '../types'
import PrioritySelect from './PrioritySelect'

import './AddTodoForm.scss'

export interface AddTodoFormProps {
  onAdd: (title: string, priority: PriorityValue) => Promise<boolean>
}

export default function AddTodoForm({ onAdd }: AddTodoFormProps) {
  const [title, setTitle] = useState('')
  const [priority, setPriority] = useState<PriorityValue>(DEFAULT_PRIORITY)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (await onAdd(title, priority)) {
      setTitle('')
      setPriority(DEFAULT_PRIORITY)
    }
  }

  return (
    <form className="add-form" onSubmit={handleSubmit}>
      <Input
        type="text"
        value={title}
        maxLength={100}
        placeholder="What needs to be done?"
        onChange={(event) => setTitle(event.target.value)}
      />
      
      <PrioritySelect value={priority} onChange={setPriority} />
      <Button variant="outline"  type="submit">Add Task</Button>
    </form>
  )
}
