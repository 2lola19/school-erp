export interface TokenResponse {
  access_token: string;
  token_type: 'bearer';
  expires_in: number;
}

export interface Workspace {
  assignment_id: string;
  role_id: string;
  name: string;
  code: string;
  category: string;
  assignment_type: 'PRIMARY' | 'SECONDARY';
  scope: Record<string, unknown>;
}

export interface UserContext {
  user_id: string;
  tenant_id: string;
  email: string;
  permission_version: number;
  permissions: string[];
  workspaces: Workspace[];
}
