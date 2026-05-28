import React, { useState, useEffect, useRef } from 'react';
import { ShieldCheck, RefreshCw } from 'lucide-react';
import SearchForm from './components/SearchForm';
import DashboardStats from './components/DashboardStats';
import LeadTable from './components/LeadTable';
import SearchHistory from './components/SearchHistory';
import LogViewer from './components/LogViewer';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export default function App() {
  const [queries, setQueries] = useState([]);
  const [activeQueryId, setActiveQueryId] = useState(null);
  const [leads, setLeads] = useState([]);
  const [totalLeads, setTotalLeads] = useState(0);
  const [stats, setStats] = useState({});
  const [logs, setLogs] = useState([]);
  const [isLogsConnected, setIsLogsConnected] = useState(false);
  const [skip, setSkip] = useState(0);
  const [isStarting, setIsStarting] = useState(false);
  const limit = 25;

  const [filters, setFilters] = useState({
    search: '',
    classification: '',
    country: ''
  });

  const isRunning = queries.some((q) => q.status === 'running' || q.status === 'pending');
  const sseRef = useRef(null);

  // 1. Fetch initial data: Stats and Search History
  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.error('Failed to fetch stats:', e);
    }
  };

  const fetchQueries = async () => {
    try {
      const res = await fetch(`${API_BASE}/queries`);
      if (res.ok) {
        const data = await res.json();
        setQueries(data);
      }
    } catch (e) {
      console.error('Failed to fetch queries:', e);
    }
  };

  const fetchLeads = async () => {
    try {
      let url = `${API_BASE}/leads?skip=${skip}&limit=${limit}`;
      if (activeQueryId) url += `&query_id=${activeQueryId}`;
      if (filters.search) url += `&search=${encodeURIComponent(filters.search)}`;
      if (filters.classification) url += `&classification=${filters.classification}`;
      if (filters.country) url += `&country=${encodeURIComponent(filters.country)}`;

      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setLeads(data.leads);
        setTotalLeads(data.total);
      }
    } catch (e) {
      console.error('Failed to fetch leads:', e);
    }
  };

  // Run on mount
  useEffect(() => {
    fetchStats();
    fetchQueries();
    fetchLeads();
  }, []);

  // Poll for stats and queries while running
  useEffect(() => {
    let interval = null;
    if (isRunning) {
      interval = setInterval(() => {
        fetchQueries();
        fetchStats();
        fetchLeads(); // refresh table in real-time
      }, 3000);
    } else {
      fetchStats();
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isRunning, activeQueryId, skip, filters]);

  // Fetch leads when query, filters, or paging changes
  useEffect(() => {
    fetchLeads();
  }, [activeQueryId, skip, filters]);

  // 2. Setup Real-time SSE Logs Stream
  useEffect(() => {
    const connectLogs = () => {
      if (sseRef.current) return;
      
      const source = new EventSource(`${API_BASE}/logs/stream`);
      sseRef.current = source;
      
      source.onopen = () => {
        setIsLogsConnected(true);
        console.log('SSE connection to logs stream established.');
      };
      
      source.onmessage = (event) => {
        setLogs((prev) => {
          const next = [...prev, event.data];
          if (next.length > 200) {
            return next.slice(next.length - 200);
          }
          return next;
        });
      };
      
      source.onerror = (err) => {
        console.error('SSE error:', err);
        setIsLogsConnected(false);
        source.close();
        sseRef.current = null;
        
        // Reconnect after 5 seconds
        setTimeout(connectLogs, 5000);
      };
    };

    connectLogs();

    return () => {
      if (sseRef.current) {
        sseRef.current.close();
        sseRef.current = null;
      }
    };
  }, []);

  // 3. Actions Handlers
  const handleSearchSubmit = async (params) => {
    setIsStarting(true);
    try {
      const res = await fetch(`${API_BASE}/queries`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
      });
      if (res.ok) {
        const newQuery = await res.json();
        // Automatically select the newly created query
        setActiveQueryId(newQuery.id);
        setSkip(0);
        await fetchQueries();
        await fetchStats();
      } else {
        const error = await res.json();
        alert(`Failed to start search: ${error.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error(e);
      alert('Network error initiating search.');
    } finally {
      setIsStarting(false);
    }
  };

  const handleSelectQuery = (id) => {
    if (activeQueryId === id) {
      // Toggle off to show all leads
      setActiveQueryId(null);
    } else {
      setActiveQueryId(id);
    }
    setSkip(0);
  };

  const handleCancelQuery = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/queries/${id}/cancel`, {
        method: 'POST'
      });
      if (res.ok) {
        fetchQueries();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteQuery = async (id) => {
    if (!confirm('Are you sure you want to delete this scrape job and all its leads?')) {
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/queries/${id}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        if (activeQueryId === id) {
          setActiveQueryId(null);
        }
        setSkip(0);
        fetchQueries();
        fetchStats();
        fetchLeads();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
    setSkip(0);
  };

  const handlePageChange = (newPageIdx) => {
    setSkip(newPageIdx * limit);
  };

  return (
    <div className="app-container">
      {/* Premium Dashboard Header */}
      <header className="header">
        <div className="brand">
          <ShieldCheck size={28} className="brand-logo" />
          <div>
            <h1>AeroLeads</h1>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              Universal Lead Intelligence & Crawling Platform
            </div>
          </div>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button
            className="btn btn-secondary btn-sm"
            style={{ width: 'auto', display: 'flex', gap: '0.25rem' }}
            onClick={() => {
              fetchQueries();
              fetchStats();
              fetchLeads();
            }}
          >
            <RefreshCw size={14} className={isRunning ? 'spin' : ''} />
            Refresh
          </button>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            v1.0.0 (Universal Mode)
          </div>
        </div>
      </header>

      {/* Main Layout Container */}
      <main className="main-content">
        {/* Statistics Widgets Row */}
        <DashboardStats stats={stats} />

        {/* Dynamic Panels Grid */}
        <div className="grid-2col">
          {/* Controls Side Column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <SearchForm onSearchSubmit={handleSearchSubmit} isRunning={isRunning} isStarting={isStarting} />
            <SearchHistory
              queries={queries}
              activeQueryId={activeQueryId}
              onSelectQuery={handleSelectQuery}
              onCancelQuery={handleCancelQuery}
              onDeleteQuery={handleDeleteQuery}
            />
          </div>

          {/* Results Main Column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <LeadTable
              leads={leads}
              total={totalLeads}
              skip={skip}
              limit={limit}
              activeQueryId={activeQueryId}
              onFilterChange={handleFilterChange}
              onPageChange={handlePageChange}
            />
            <LogViewer logs={logs} isConnected={isLogsConnected} />
          </div>
        </div>
      </main>
    </div>
  );
}
