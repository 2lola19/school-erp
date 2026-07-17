import { getPendingQueue, removeFromQueue } from './db';
import { apiClient } from '../api-client';
import { addToSyncQueue } from './db';

let isSyncing = false;

export const processSyncQueue = async () => {
  if (typeof window === 'undefined' || !navigator.onLine || isSyncing) return;
  
  isSyncing = true;
  try {
    const queue = await getPendingQueue();
    if (queue.length === 0) {
      isSyncing = false;
      return;
    }

    console.log(`[*] Initiating network flush for ${queue.length} pending mutations...`);
    let successfulSyncs = 0;

    for (const item of queue) {
      try {
        const method = item.method.toUpperCase();
        
        if (method === 'POST') {
          await apiClient.post(item.endpoint, item.payload);
        } else if (method === 'PUT') {
          await apiClient.put(item.endpoint, item.payload);
        } else if (method === 'DELETE') {
          await apiClient.delete(item.endpoint, { data: item.payload });
        }
        
        await removeFromQueue(item.id);
        successfulSyncs++;
        console.log(`[+] Successfully synced and purged mutation: ${item.id}`);
      } catch (error) {
        console.error(`[-] Sync failed for mutation ${item.id}. Retaining in ledger.`, error);
      }
    }

    // BROADCAST SIGNAL: If at least one item synced, alert the React lifecycle
    if (successfulSyncs > 0) {
      window.dispatchEvent(new CustomEvent('offline-sync-complete'));
    }

  } finally {
    isSyncing = false;
  }
};

export const initSyncListeners = () => {
  if (typeof window === 'undefined') return;
  
  // Trigger immediate flush when connection is restored
  window.addEventListener('online', () => {
    console.log('[*] Network link restored. Triggering autonomous sync...');
    processSyncQueue();
  });

  // Temporal fallback: attempt flush every 60 seconds if online
  setInterval(processSyncQueue, 60000);
};

export const safeMutate = async (method: 'POST' | 'PUT' | 'DELETE', endpoint: string, payload: any) => {
  // 1. Attempt live network execution if browser reports online
  if (typeof window !== 'undefined' && navigator.onLine) {
    try {
      let response;
      if (method === 'POST') response = await apiClient.post(endpoint, payload);
      if (method === 'PUT') response = await apiClient.put(endpoint, payload);
      if (method === 'DELETE') response = await apiClient.delete(endpoint, { data: payload });
      return { success: true, offline: false, data: response?.data };
    } catch (error: any) {
      // 2. If failure is a network drop (no server response), route to local ledger
      if (!error.response) {
        console.warn('[-] Network unreached. Routing payload to local ledger.');
        await addToSyncQueue(endpoint, method, payload);
        return { success: true, offline: true };
      }
      // 3. If failure is a strict backend rejection (e.g., 400 Bad Request), throw it
      throw error;
    }
  } else {
    // 4. Browser is explicitly offline. Route to local ledger immediately.
    console.warn('[-] System offline. Routing payload to local ledger.');
    await addToSyncQueue(endpoint, method, payload);
    return { success: true, offline: true };
  }
};