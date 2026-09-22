import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { PRIORITY_OPTIONS } from '../priorities'
import type { PriorityValue } from '../types'

interface PrioritySelectProps {
  value: PriorityValue
  onChange: (value: PriorityValue) => void
}

export default function PrioritySelect({ value, onChange }: PrioritySelectProps) {
  return (
    <Select 
      value={value.toString()} 
      onValueChange={(val: string) => onChange(Number(val) as PriorityValue)}
    >
      <SelectTrigger className="w-[130px]">
        <SelectValue placeholder="Priority" />
      </SelectTrigger>
      <SelectContent position="popper" sideOffset={4} className="bg-popover z-50 border shadow-md">
        {PRIORITY_OPTIONS.map((option) => (
          <SelectItem key={option.value} value={option.value.toString()}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}