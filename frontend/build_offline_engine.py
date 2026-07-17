import os

os.makedirs("src/lib", exist_ok=True)

# 1. Build the IndexedDB Queue Manager
queue_code = """
export const initDB = () => {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('OfflineSyncDB', 1)
    
    request.onupgradeneeded = (e: any) => {
      const db = e.target.result
      if (!db.objectStoreNames.contains('mutations')) {
        db.createObjectStore('mutations', { keyPath: 'id', autoIncrement: true })
      }
    }
    
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

export const queueMutation = async (config: any) => {
  const db: any = await initDB()
  const tx = db.transaction('mutations', 'readwrite')
  const store = tx.objectStore('mutations')
  
  const payload = {
    url: config.url,
    method: config.method,
    data: config.data,
    headers: config.headers,
    timestamp: Date.now()
  }
  
  store.add(payload)
  console.log('[*] Network offline. Mutation written to local queue.')
}

export const processQueue = async (apiClient: any) => {
  const db: any = await initDB()
  const tx = db.transaction('mutations', 'readonly')
  const store = tx.objectStore('mutations')
  const request = store.getAll()

  request.onsuccess = async () => {
    const items = request.result
    if (items.length === 0) return
    
    console.log(`[*] Network restored. Processing ${items.length} queued mutations.`)
    
    for (const item of items) {
      try {
        await apiClient({
          url: item.url,
          method: item.method,
          data: item.data,
          headers: item.headers
        })
        
        // Delete item on success to prevent duplicate execution
        const delTx = db.transaction('mutations', 'readwrite')
        delTx.objectStore('mutations').delete(item.id)
      } catch (e: any) {
        if (e.response && e.response.status >= 400 && e.response.status < 500) {
          // Client error (e.g. duplicate constraint). Drop it to prevent blocking the queue.
          const delTx = db.transaction('mutations', 'readwrite')
          delTx.objectStore('mutations').delete(item.id)
        } else {
          // Server error or network drop. Halt processing to maintain strict order.
          console.log('[-] Sync halted. Will retry later.')
          break
        }
      }
    }
  }
}
"""
with open("src/lib/sync-queue.ts", "w", encoding="utf-8") as f:
    f.write(queue_code.strip() + "\n")
print("[+] IndexedDB synchronization queue built.")

# 2. Patch the Axios Client
client_file = "src/lib/api-client.ts"
if os.path.exists(client_file):
    with open(client_file, "r", encoding="utf-8") as f:
        content = f.read()
        
    patch = """
// OFFLINE SYNC INTERCEPTOR
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    // If no response exists, it is a hard network failure
    if (!error.response && error.config && error.config.method !== 'get') {
      const { queueMutation } = await import('./sync-queue')
      await queueMutation(error.config)
      return Promise.resolve({ data: { offline: true, detail: 'Device offline. Action queued for sync.' } })
    }
    return Promise.reject(error)
  }
)

// BIND SYNC PROCESSOR TO NETWORK RESTORATION
if (typeof window !== 'undefined') {
  window.addEventListener('online', async () => {
    const { processQueue } = await import('./sync-queue')
    await processQueue(apiClient)
  })
}
"""
    if "OFFLINE SYNC INTERCEPTOR" not in content:
        with open(client_file, "a", encoding="utf-8") as f:
            f.write("\n" + patch.strip() + "\n")
        print("[+] Axios interceptor patched for offline mutation trapping.")
    else:
        print("[*] Axios client already patched.")
else:
    print("[-] Critical error. Could not locate src/lib/api-client.ts")