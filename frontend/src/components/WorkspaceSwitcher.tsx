'use client';

import { useAuthStore } from '@/store/authStore';

export function WorkspaceSwitcher() {
  const { activeWorkspaceId, profile, setActiveWorkspace } = useAuthStore();
  if (!profile || profile.workspaces.length < 2) return null;

  return (
    <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
      Current workspace
      <select
        value={activeWorkspaceId ?? ''}
        onChange={(event) => setActiveWorkspace(event.target.value)}
        className="h-10 rounded-md border bg-white px-3"
      >
        {profile.workspaces.map((workspace) => (
          <option key={workspace.assignment_id} value={workspace.assignment_id}>
            {workspace.name}{workspace.assignment_type === 'PRIMARY' ? ' (Primary)' : ''}
          </option>
        ))}
      </select>
    </label>
  );
}
