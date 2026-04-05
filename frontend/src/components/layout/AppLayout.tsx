import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import { Toaster } from 'sonner'

export default function AppLayout() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto bg-background p-6">
        <div className="mx-auto max-w-6xl">
          <Outlet />
        </div>
      </main>
      <Toaster />
    </div>
  )
}
