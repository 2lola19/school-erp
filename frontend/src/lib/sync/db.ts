import { openDB, DBSchema, IDBPDatabase } from 'idb';

interface SchoolSyncDB extends DBSchema {
  sync_queue: {
    key: string;
    value: {
      id: string;
      endpoint: string;
      method: string;
      payload: any;
      timestamp: number;
      status: 'pending' | 'failed';
      retry_count: number;
    };
    indexes: { 'by-status': string };
  };
}

let dbPromise: Promise<IDBPDatabase<SchoolSyncDB>> | null = null;

export const getSyncDB = () => {
  if (typeof window === 'undefined') return null;
  
  if (!dbPromise) {
    dbPromise = openDB<SchoolSyncDB>('school_offline_db', 1, {
      upgrade(db) {
        if (!db.objectStoreNames.contains('sync_queue')) {
          const store = db.createObjectStore('sync_queue', { keyPath: 'id' });
          store.createIndex('by-status', 'status');
        }
      },
    });
  }
  return dbPromise;
};

export const addToSyncQueue = async (endpoint: string, method: string, payload: any) => {
  const db = await getSyncDB();
  if (!db) return;

  const id = crypto.randomUUID();
  await db.add('sync_queue', {
    id,
    endpoint,
    method,
    payload,
    timestamp: Date.now(),
    status: 'pending',
    retry_count: 0
  });
  
  return id;
};

export const getPendingQueue = async () => {
  const db = await getSyncDB();
  if (!db) return [];
  return await db.getAllFromIndex('sync_queue', 'by-status', 'pending');
};

export const removeFromQueue = async (id: string) => {
  const db = await getSyncDB();
  if (!db) return;
  await db.delete('sync_queue', id);
};