/**
 * PisoHeroes Cache Manager
 * Client-side caching system for improved performance and offline support
 */

const CacheManager = {
    version: '1.0.0',
    
    // Cache keys
    keys: {
        expenses: 'pisoheroes_expenses_cache',
        darkMode: 'pisoheroes_dark_mode',
        lastCategory: 'pisoheroes_last_category',
        favorites: 'pisoheroes_favorites',
        pendingOps: 'pisoheroes_pending_ops',
        cacheVersion: 'pisoheroes_cache_version',
        lastSync: 'pisoheroes_last_sync'
    },
    
    // Initialize cache system
    init: function() {
        this.checkVersion();
        this.applyDarkMode();
        this.checkOnlineStatus();
        this.setupEventListeners();
        console.log('PisoHeroes Cache Manager initialized');
    },
    
    // Check and update cache version
    checkVersion: function() {
        const storedVersion = localStorage.getItem(this.keys.cacheVersion);
        if (storedVersion !== this.version) {
            console.log('Cache version mismatch. Clearing old cache.');
            this.clearAll();
            localStorage.setItem(this.keys.cacheVersion, this.version);
        }
    },
    
    // Get item from cache
    get: function(key) {
        try {
            const item = localStorage.getItem(key);
            if (!item) return null;
            
            const data = JSON.parse(item);
            
            // Check if cached data is expired (30 days)
            if (data.timestamp) {
                const age = Date.now() - new Date(data.timestamp).getTime();
                const maxAge = 30 * 24 * 60 * 60 * 1000; // 30 days in milliseconds
                
                if (age > maxAge) {
                    console.log(`Cache expired for ${key}`);
                    this.invalidate(key);
                    return null;
                }
            }
            
            return data.data;
        } catch (e) {
            console.error('Error reading from cache:', e);
            return null;
        }
    },
    
    // Set item in cache
    set: function(key, data) {
        try {
            const cacheData = {
                version: this.version,
                timestamp: new Date().toISOString(),
                data: data
            };
            localStorage.setItem(key, JSON.stringify(cacheData));
            
            // Update last sync time
            localStorage.setItem(this.keys.lastSync, new Date().toISOString());
            
            return true;
        } catch (e) {
            console.error('Error writing to cache:', e);
            // Handle quota exceeded
            if (e.name === 'QuotaExceededError') {
                this.clearOldestCache();
                // Try again after clearing
                try {
                    localStorage.setItem(key, JSON.stringify({
                        version: this.version,
                        timestamp: new Date().toISOString(),
                        data: data
                    }));
                } catch (e2) {
                    console.error('Failed to write after clearing:', e2);
                    return false;
                }
            }
            return false;
        }
    },
    
    // Invalidate specific cache
    invalidate: function(key) {
        localStorage.removeItem(key);
        console.log(`Cache invalidated: ${key}`);
    },
    
    // Clear all caches
    clearAll: function() {
        Object.values(this.keys).forEach(key => {
            localStorage.removeItem(key);
        });
        console.log('All caches cleared');
    },
    
    // Clear oldest cache to free up space
    clearOldestCache: function() {
        const keys = Object.values(this.keys);
        let oldestKey = null;
        let oldestTime = Date.now();
        
        keys.forEach(key => {
            const item = localStorage.getItem(key);
            if (item) {
                try {
                    const data = JSON.parse(item);
                    const timestamp = new Date(data.timestamp).getTime();
                    if (timestamp < oldestTime) {
                        oldestTime = timestamp;
                        oldestKey = key;
                    }
                } catch (e) {
                    // Invalid data, remove it
                    localStorage.removeItem(key);
                }
            }
        });
        
        if (oldestKey) {
            this.invalidate(oldestKey);
        }
    },
    
    // Get cache size
    getCacheSize: function() {
        let totalSize = 0;
        for (let key in localStorage) {
            if (localStorage.hasOwnProperty(key)) {
                totalSize += localStorage[key].length + key.length;
            }
        }
        return totalSize;
    },
    
    // Format cache size for display
    formatCacheSize: function() {
        const size = this.getCacheSize();
        if (size < 1024) return size + ' bytes';
        if (size < 1024 * 1024) return (size / 1024).toFixed(2) + ' KB';
        return (size / (1024 * 1024)).toFixed(2) + ' MB';
    },
    
    // Get last sync time
    getLastSync: function() {
        const lastSync = localStorage.getItem(this.keys.lastSync);
        if (!lastSync) return 'Never';
        
        const date = new Date(lastSync);
        const now = new Date();
        const diff = now - date;
        
        const minutes = Math.floor(diff / 60000);
        if (minutes < 1) return 'Just now';
        if (minutes < 60) return minutes + ' minutes ago';
        
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return hours + ' hours ago';
        
        const days = Math.floor(hours / 24);
        return days + ' days ago';
    },
    
    // Dark mode functions
    applyDarkMode: function() {
        const darkMode = localStorage.getItem(this.keys.darkMode);
        if (darkMode === 'true') {
            document.body.classList.add('dark-theme');
            const toggle = document.getElementById('darkModeToggle');
            if (toggle) toggle.checked = true;
        }
    },
    
    toggleDarkMode: function() {
        const isDark = document.body.classList.toggle('dark-theme');
        localStorage.setItem(this.keys.darkMode, isDark);
        console.log('Dark mode:', isDark ? 'enabled' : 'disabled');
    },
    
    // Online/Offline status
    checkOnlineStatus: function() {
        const updateStatus = () => {
            const online = navigator.onLine;
            const indicator = document.getElementById('offlineIndicator');
            
            if (indicator) {
                if (online) {
                    indicator.classList.add('d-none');
                    // Sync pending operations when back online
                    this.syncPendingOperations();
                } else {
                    indicator.classList.remove('d-none');
                }
            }
            
            // Disable/enable buttons based on online status
            const addButtons = document.querySelectorAll('[data-requires-online]');
            addButtons.forEach(btn => {
                btn.disabled = !online;
                if (!online) {
                    btn.title = 'This action requires an internet connection';
                }
            });
        };
        
        updateStatus();
        window.addEventListener('online', updateStatus);
        window.addEventListener('offline', updateStatus);
    },
    
    setupEventListeners: function() {
        // Dark mode toggle
        const darkModeToggle = document.getElementById('darkModeToggle');
        if (darkModeToggle) {
            darkModeToggle.addEventListener('change', () => this.toggleDarkMode());
        }
        
        // Clear cache button
        const clearCacheBtn = document.getElementById('clearCacheBtn');
        if (clearCacheBtn) {
            clearCacheBtn.addEventListener('click', () => {
                if (confirm('Are you sure you want to clear all cached data?')) {
                    this.clearAll();
                    location.reload();
                }
            });
        }
        
        // Sync button
        const syncBtn = document.getElementById('syncBtn');
        if (syncBtn) {
            syncBtn.addEventListener('click', () => this.syncPendingOperations());
        }
    },
    
    // Expense caching
    cacheExpenses: function(expenses) {
        return this.set(this.keys.expenses, expenses);
    },
    
    getCachedExpenses: function() {
        return this.get(this.keys.expenses);
    },
    
    invalidateExpenses: function() {
        this.invalidate(this.keys.expenses);
    },
    
    // Last category
    setLastCategory: function(category) {
        localStorage.setItem(this.keys.lastCategory, category);
    },
    
    getLastCategory: function() {
        return localStorage.getItem(this.keys.lastCategory);
    },
    
    // Favorites
    addFavorite: function(item) {
        const favorites = this.get(this.keys.favorites) || [];
        
        // Check if already exists
        const exists = favorites.some(fav => 
            fav.category === item.category && fav.amount === item.amount
        );
        
        if (!exists) {
            favorites.unshift(item);
            // Keep only top 10
            if (favorites.length > 10) {
                favorites.pop();
            }
            this.set(this.keys.favorites, favorites);
        }
    },
    
    getFavorites: function() {
        return this.get(this.keys.favorites) || [];
    },
    
    removeFavorite: function(index) {
        const favorites = this.get(this.keys.favorites) || [];
        favorites.splice(index, 1);
        this.set(this.keys.favorites, favorites);
    },
    
    // Pending operations (for offline support)
    addPendingOperation: function(operation) {
        const pending = this.get(this.keys.pendingOps) || [];
        pending.push({
            ...operation,
            timestamp: new Date().toISOString()
        });
        this.set(this.keys.pendingOps, pending);
    },
    
    getPendingOperations: function() {
        return this.get(this.keys.pendingOps) || [];
    },
    
    clearPendingOperations: function() {
        this.invalidate(this.keys.pendingOps);
    },
    
    syncPendingOperations: async function() {
        if (!navigator.onLine) {
            console.log('Cannot sync: offline');
            return;
        }
        
        const pending = this.getPendingOperations();
        if (pending.length === 0) {
            console.log('No pending operations to sync');
            return;
        }
        
        console.log(`Syncing ${pending.length} pending operations...`);
        
        const syncBtn = document.getElementById('syncBtn');
        if (syncBtn) {
            syncBtn.disabled = true;
            syncBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Syncing...';
        }
        
        let successCount = 0;
        const failedOps = [];
        
        for (const op of pending) {
            try {
                const response = await fetch(op.url, {
                    method: op.method,
                    headers: op.headers || {},
                    body: op.body ? JSON.stringify(op.body) : null
                });
                
                if (response.ok) {
                    successCount++;
                } else {
                    failedOps.push(op);
                }
            } catch (e) {
                console.error('Failed to sync operation:', e);
                failedOps.push(op);
            }
        }
        
        // Update pending operations with only failed ones
        if (failedOps.length > 0) {
            this.set(this.keys.pendingOps, failedOps);
        } else {
            this.clearPendingOperations();
        }
        
        if (syncBtn) {
            syncBtn.disabled = false;
            syncBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Sync';
        }
        
        // Show result
        const message = `Synced ${successCount}/${pending.length} operations`;
        if (failedOps.length > 0) {
            alert(message + `\n${failedOps.length} operations failed and will be retried.`);
        } else {
            console.log(message);
            // Reload to show updated data
            location.reload();
        }
    }
};

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => CacheManager.init());
} else {
    CacheManager.init();
}

// Expose to window for access from other scripts
window.CacheManager = CacheManager;
