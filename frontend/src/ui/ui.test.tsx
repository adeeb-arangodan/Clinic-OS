import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import i18n from '@/lib/i18n'
import { DataTable, type DataTableColumn } from '@/ui/DataTable'
import { DualDate } from '@/ui/DualDate'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/ui/Select'
import { StatusChip } from '@/ui/StatusChip'

beforeEach(async () => {
  await i18n.changeLanguage('en')
})

describe('StatusChip', () => {
  it('applies the docs/03 §5.2 chip palette per kind', () => {
    render(<StatusChip kind="eligible">Eligible</StatusChip>)
    expect(screen.getByText('Eligible')).toHaveClass('bg-chip-eligible-bg')

    render(<StatusChip kind="rejected">Rejected</StatusChip>)
    expect(screen.getByText('Rejected')).toHaveClass('bg-chip-rejected-bg')
  })
})

describe('DualDate', () => {
  it('renders Gregorian with a Hijri secondary line', () => {
    render(<DualDate date="2026-07-06T09:00:00Z" />)
    // 6 Jul 2026 ≈ 21 Muharram 1448 AH (Umm al-Qura)
    expect(screen.getByText(/2026/)).toBeInTheDocument()
    expect(screen.getByText(/1448/)).toBeInTheDocument()
  })

  it('uses Arabic-locale formatting when the UI is Arabic', async () => {
    await i18n.changeLanguage('ar')
    const { container } = render(<DualDate date="2026-07-06T09:00:00Z" />)
    expect(container.textContent).toContain('محرم') // Hijri month name in Arabic
  })

  it('can hide the Hijri line', () => {
    render(<DualDate date="2026-07-06T09:00:00Z" showHijri={false} />)
    expect(screen.queryByText(/1448/)).not.toBeInTheDocument()
  })
})

interface Row {
  id: string
  name: string
}

const columns: DataTableColumn<Row>[] = [
  { key: 'name', header: 'Name', cell: (row) => row.name },
]

describe('DataTable', () => {
  it('renders rows and wires cursor pagination buttons', async () => {
    const onNext = vi.fn()
    const onPrev = vi.fn()
    render(
      <DataTable
        columns={columns}
        rows={[{ id: '1', name: 'Alpha' }]}
        rowKey={(row) => row.id}
        pagination={{ hasPrev: false, hasNext: true, onNext, onPrev }}
      />,
    )

    expect(screen.getByText('Alpha')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(onNext).toHaveBeenCalledOnce()
  })

  it('shows loading, error and empty states', () => {
    const { rerender } = render(
      <DataTable columns={columns} rows={[]} rowKey={(row: Row) => row.id} isPending />,
    )
    expect(screen.getByText('Loading…')).toBeInTheDocument()

    rerender(<DataTable columns={columns} rows={[]} rowKey={(row: Row) => row.id} isError />)
    expect(screen.getByText(/Could not reach the server/)).toBeInTheDocument()

    rerender(
      <DataTable columns={columns} rows={[]} rowKey={(row: Row) => row.id} emptyLabel="No rows" />,
    )
    expect(screen.getByText('No rows')).toBeInTheDocument()
  })
})

describe('Select', () => {
  it('renders the trigger with placeholder and options', () => {
    render(
      <Select>
        <SelectTrigger aria-label="Status">
          <SelectValue placeholder="Pick one" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="a">Option A</SelectItem>
        </SelectContent>
      </Select>,
    )
    expect(screen.getByRole('combobox', { name: 'Status' })).toHaveTextContent('Pick one')
  })
})
