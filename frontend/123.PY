python -c "content = '''\'use client\';
import { useState } from \'react\';
import { useRouter } from \'next/navigation\';
import { useAuthStore } from \'@/store/authStore\';
import { Button } from \'@/components/ui/button\';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from \'@/components/ui/card\';

export default function LoginPage() {
  const [email, setEmail] = useState(\'\');
  const [password, setPassword] = useState(\'\');
  const [error, setError] = useState(\'\');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const { login } = useAuthStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(\'\');
    
    try {
      const res = await login(email, password);
      const tokenStr = res.data.access_token || res.data.token;
      const base64Url = tokenStr.split(\'.\')[1];
      const base64 = base64Url.replace(/-/g, \'+\').replace(/_/g, \'/\');
      const payload = JSON.parse(window.atob(base64));

      if (payload.permissions && payload.permissions.includes(\'view_all_tenants\')) {
        router.push(\'/superadmin\');
      } else {
        router.push(\'/school\');
      }
    } catch (err: any) {
      setError(\'Invalid credentials\');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className=\"min-h-screen flex items-center justify-center bg-slate-50\">
      <Card className=\"w-full max-w-md\">
        <CardHeader className=\"space-y-1\">
          <CardTitle className=\"text-2xl font-bold\">System Login</CardTitle>
          <CardDescription>Enter your credentials to access your control plane</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className=\"space-y-4\">
            <div className=\"space-y-2\">
              <label className=\"text-sm font-medium\">Email</label>
              <input required type=\"email\" value={email} onChange={(e) => setEmail(e.target.value)} className=\"flex h-10 w-full rounded-md border px-3 py-2 text-sm\" />
            </div>
            <div className=\"space-y-2\">
              <label className=\"text-sm font-medium\">Password</label>
              <input required type=\"password\" value={password} onChange={(e) => setPassword(e.target.value)} className=\"flex h-10 w-full rounded-md border px-3 py-2 text-sm\" />
            </div>
            {error && <div className=\"text-sm text-red-500\">{error}</div>}
            <Button className=\"w-full\" type=\"submit\" disabled={isLoading}>
              {isLoading ? \'Authenticating...\' : \'Sign In\'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
'''; open('src/app/(auth)/login/page.tsx', 'w', encoding='utf-8').write(content); print('[+] Frontend login router explicitly overwritten.')"
