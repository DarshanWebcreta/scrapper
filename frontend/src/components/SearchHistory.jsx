import React from 'react';
import { History, XCircle, Trash2, Filter } from 'lucide-react';

export default function SearchHistory({
  queries,
  activeQueryId,
  onSelectQuery,
  onCancelQuery,
  onDeleteQuery
}) {
  return (
    <div className="card">
      <h2 className="card-title">
        <History size={18} className="brand-logo" />
        Search History
      </h2>
      <div style={{ maxHeight: '420px', overflowY: 'auto', paddingRight: '0.25rem' }}>
        {queries.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            No scrape history found.
          </div>
        ) : (
          queries.map((q) => {
            const isSelected = activeQueryId === q.id;
            const formattedDate = new Date(q.created_at).toLocaleDateString(undefined, {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit'
            });

            // Handle country presentation formats
            const getCountriesText = () => {
              if (!q.countries) return '';
              if (Array.isArray(q.countries)) {
                return q.countries.length > 0 ? q.countries.join(', ') : 'Global';
              }
              return String(q.countries);
            };

            return (
              <div
                key={q.id}
                className="history-item"
                style={{
                  borderColor: isSelected ? 'var(--color-primary)' : 'var(--border-color)',
                  background: isSelected ? 'rgba(59, 130, 246, 0.05)' : 'rgba(255, 255, 255, 0.01)'
                }}
              >
                <div className="history-details" style={{ flex: 1 }}>
                  <div
                    style={{
                      fontWeight: 600,
                      color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.25rem'
                    }}
                    onClick={() => onSelectQuery(q.id)}
                    title="Click to filter leads by this query"
                  >
                    {q.query || q.keyword || 'Search Run'}
                    {isSelected && <Filter size={12} className="brand-logo" />}
                  </div>
                  
                  <div className="history-meta">
                    {getCountriesText() && <span>{getCountriesText()} • </span>}
                    <span>{formattedDate}</span>
                  </div>

                  {q.status === 'running' && (
                    <div className="progress-container" style={{ marginTop: '0.5rem', width: '90%' }}>
                      <div className="progress-header" style={{ fontSize: '0.7rem', marginBottom: '0.2rem' }}>
                        <span>Crawling ({q.total_crawled}/{q.total_discovered})</span>
                        <span>{q.progress}%</span>
                      </div>
                      <div className="progress-bar-bg" style={{ height: '4px' }}>
                        <div className="progress-bar-fill" style={{ width: `${q.progress}%` }}></div>
                      </div>
                    </div>
                  )}
                  
                  <div style={{ marginTop: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className={`badge badge-${q.status}`} style={{ fontSize: '0.65rem', padding: '0.1rem 0.4rem' }}>
                      {q.status}
                    </span>
                    {q.total_leads > 0 && (
                      <span style={{ fontSize: '0.75rem', color: 'var(--color-success)', fontWeight: 500 }}>
                        {q.total_leads} leads
                      </span>
                    )}
                  </div>
                </div>

                <div className="history-actions">
                  {(q.status === 'running' || q.status === 'pending') && (
                    <button
                      className="btn btn-secondary btn-sm"
                      style={{ padding: '0.25rem', width: 'auto', border: 'none', color: 'var(--color-warning)' }}
                      onClick={() => onCancelQuery(q.id)}
                      title="Cancel Search"
                    >
                      <XCircle size={16} />
                    </button>
                  )}
                  <button
                    className="btn btn-secondary btn-sm"
                    style={{ padding: '0.25rem', width: 'auto', border: 'none', color: 'var(--color-danger)' }}
                    onClick={() => onDeleteQuery(q.id)}
                    title="Delete Search"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
