import React, { useEffect, useRef } from 'react';
import { Terminal } from 'lucide-react';

export default function LogViewer({ logs, isConnected }) {
  const containerRef = useRef(null);

  // Auto scroll to bottom on new logs
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  const getLogClass = (line) => {
    const lower = line.toLowerCase();
    if (lower.includes('[error]')) return 'log-line error';
    if (lower.includes('[warning]') || lower.includes('[warn]')) return 'log-line warn';
    if (lower.includes('[app]') || lower.includes('[main]')) return 'log-line app';
    return 'log-line info';
  };

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
      <h2
        className="card-title"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: 'none',
          paddingBottom: 0,
          marginBottom: '1rem'
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Terminal size={18} className="brand-logo" />
          System Activity Monitor
        </span>
        <span
          className="badge"
          style={{
            backgroundColor: isConnected ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
            color: isConnected ? 'var(--color-success)' : 'var(--color-danger)',
            fontSize: '0.7rem',
            border: 'none',
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem'
          }}
        >
          <span
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: isConnected ? 'var(--color-success)' : 'var(--color-danger)',
              display: 'inline-block',
              animation: isConnected ? 'pulse 2s infinite' : 'none'
            }}
          />
          {isConnected ? 'Live Stream' : 'Disconnected'}
        </span>
      </h2>

      <div className="log-monitor" ref={containerRef}>
        {logs.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            Awaiting scraping job logs...
          </div>
        ) : (
          logs.map((log, idx) => (
            <div key={idx} className={getLogClass(log)}>
              {log}
            </div>
          ))
        )}
      </div>
      
      <style>{`
        @keyframes pulse {
          0% { opacity: 0.4; }
          50% { opacity: 1; }
          100% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}
