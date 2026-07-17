import os

dirs = [
    "src/app/(auth)/login",
    "src/app/(dashboard)/superadmin",
    "src/components/ui",
    "src/components/forms",
    "src/components/layouts",
    "src/hooks",
    "src/lib",
    "src/store",
    "src/types"
]

files = [
    "src/app/(auth)/login/page.tsx",
    "src/components/forms/LoginForm.tsx",
    "src/hooks/useAuth.ts",
    "src/lib/api-client.ts",
    "src/store/authStore.ts",
    "src/types/api.d.ts",
    ".env.local"
]

for d in dirs:
    os.makedirs(d, exist_ok=True)

for f in files:
    with open(f, 'a') as file_obj:
        pass

print("Frontend directory structure generated successfully.")