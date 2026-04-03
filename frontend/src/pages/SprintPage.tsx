import { useState } from 'react'
import { Kanban, Plus } from 'lucide-react'
import { useTasks, useUpdateTaskStatus, useCreateTask, useDeleteTask } from '../hooks/useTasks'
import { useProjects } from '../hooks/useProjects'
import type { Task, TaskStatus } from '../api/client'

const COLUMNS: { key: TaskStatus; label: string; color: string }[] = [
  { key: 'todo',        label: 'TO DO',       color: 'text-slate-400' },
  { key: 'in_progress', label: 'IN PROGRESS', color: 'text-neon-amber' },
  { key: 'done',        label: 'DONE',        color: 'text-neon-green' },
]

const PRIORITY_COLOR: Record<string, string> = {
  high:   'text-neon-red border-neon-red/30 bg-neon-red/10',
  medium: 'text-neon-amber border-neon-amber/30 bg-neon-amber/10',
  low:    'text-slate-500 border-dark-600 bg-dark-700',
}

function TaskCard({ task, onDelete }: { task: Task; onDelete: (id: string) => void }) {
  const [dragging, setDragging] = useState(false)
  return (
    <div
      draggable
      onDragStart={() => setDragging(true)}
      onDragEnd={() => setDragging(false)}
      className={`bg-dark-700 border border-dark-600 rounded p-3 cursor-grab active:cursor-grabbing transition-opacity ${dragging ? 'opacity-40' : ''}`}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm text-slate-200 flex-1">{task.title}</p>
        <button onClick={() => onDelete(task.id!)} className="text-slate-700 hover:text-neon-red transition-colors text-xs shrink-0">✕</button>
      </div>
      <div className="flex items-center gap-2 mt-2">
        <span className={`text-xs font-mono border px-1.5 py-0.5 rounded ${PRIORITY_COLOR[task.priority]}`}>
          {task.priority}
        </span>
        <span className="text-xs text-slate-600">{task.project_id}</span>
      </div>
    </div>
  )
}

export default function SprintPage() {
  const { data: tasks = [] }    = useTasks()
  const { data: projects = [] } = useProjects()
  const { mutate: moveTask }    = useUpdateTaskStatus()
  const { mutate: deleteTask }  = useDeleteTask()
  const { mutate: addTask }     = useCreateTask()

  const [newTitle, setNewTitle]       = useState('')
  const [newProject, setNewProject]   = useState('')
  const [newPriority, setNewPriority] = useState<'high' | 'medium' | 'low'>('medium')
  const [showForm, setShowForm]       = useState(false)

  function handleDrop(e: React.DragEvent, status: TaskStatus) {
    const id = e.dataTransfer.getData('taskId')
    if (id) moveTask({ id, status })
  }

  function handleDragStart(e: React.DragEvent, id: string) {
    e.dataTransfer.setData('taskId', id)
  }

  function handleAddTask(e: React.FormEvent) {
    e.preventDefault()
    if (!newTitle.trim() || !newProject) return
    addTask({ project_id: newProject, title: newTitle.trim(), description: '', priority: newPriority, tags: [] })
    setNewTitle('')
    setShowForm(false)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Kanban size={18} className="text-brand" />
          <h1 className="font-game font-bold text-xl text-slate-100 tracking-wide">SPRINT BOARD</h1>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1.5 text-xs font-game font-bold tracking-wider px-3 py-1.5 rounded bg-brand/10 border border-brand/30 text-brand hover:bg-brand/20 transition-all"
        >
          <Plus size={12} /> ADD TASK
        </button>
      </div>

      {/* Add task form */}
      {showForm && (
        <form onSubmit={handleAddTask} className="bg-dark-800 border border-dark-600 rounded-lg p-4 mb-6 flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-48">
            <label className="text-xs font-mono text-slate-500 block mb-1">Task title</label>
            <input
              value={newTitle}
              onChange={e => setNewTitle(e.target.value)}
              placeholder="What needs to be done?"
              required
              className="w-full bg-dark-700 border border-dark-600 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-brand"
            />
          </div>
          <div>
            <label className="text-xs font-mono text-slate-500 block mb-1">Project</label>
            <select
              value={newProject}
              onChange={e => setNewProject(e.target.value)}
              required
              className="bg-dark-700 border border-dark-600 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-brand"
            >
              <option value="">Select…</option>
              {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs font-mono text-slate-500 block mb-1">Priority</label>
            <select
              value={newPriority}
              onChange={e => setNewPriority(e.target.value as 'high' | 'medium' | 'low')}
              className="bg-dark-700 border border-dark-600 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-brand"
            >
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
          <button type="submit" className="px-4 py-2 rounded bg-brand/10 border border-brand/30 text-brand text-sm font-game font-bold tracking-wider hover:bg-brand/20 transition-all">
            ADD
          </button>
        </form>
      )}

      {/* Kanban columns */}
      <div className="grid grid-cols-3 gap-4">
        {COLUMNS.map(col => (
          <div
            key={col.key}
            className="bg-dark-800 border border-dark-600 rounded-lg p-4 min-h-80"
            onDragOver={e => e.preventDefault()}
            onDrop={e => handleDrop(e, col.key)}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className={`font-game font-bold text-xs tracking-widest ${col.color}`}>{col.label}</h3>
              <span className="text-xs font-mono text-slate-600">
                {tasks.filter(t => t.status === col.key).length}
              </span>
            </div>
            <div className="space-y-2">
              {tasks
                .filter(t => t.status === col.key)
                .map(task => (
                  <div
                    key={task.id}
                    draggable
                    onDragStart={e => handleDragStart(e, task.id!)}
                  >
                    <TaskCard
                      task={task}
                      onDelete={deleteTask}
                    />
                  </div>
                ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
