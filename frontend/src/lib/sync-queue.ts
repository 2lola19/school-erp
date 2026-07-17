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
