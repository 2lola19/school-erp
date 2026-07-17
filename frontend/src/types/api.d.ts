export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface TokenPayload {
  sub: string;
  tenant_id: string;
  role: string;
  exp: number;
}