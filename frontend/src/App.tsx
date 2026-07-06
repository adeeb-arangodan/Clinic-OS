import { Navigate, Route, Routes } from 'react-router-dom'

import { AppShell } from '@/components/AppShell'
import { RequireAuth, RequirePermission } from '@/features/auth/guards'
import { LoginPage } from '@/features/auth/LoginPage'
import { AuditLogPage } from '@/features/audit/AuditLogPage'
import { HomePage } from '@/features/home/HomePage'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route index element={<HomePage />} />
          <Route element={<RequirePermission permission="admin.view_audit" />}>
            <Route path="audit-logs" element={<AuditLogPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
