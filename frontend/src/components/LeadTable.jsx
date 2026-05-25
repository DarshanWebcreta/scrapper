import React, { useState } from 'react';
import { Download, ExternalLink, Eye, X, Globe, MapPin, Briefcase, FileText } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export default function LeadTable({
  leads,
  total,
  skip,
  limit,
  activeQueryId,
  onFilterChange,
  onPageChange
}) {
  const [selectedLead, setSelectedLead] = useState(null);
  const [searchText, setSearchText] = useState('');
  const [classification, setClassification] = useState('');
  const [countryFilter, setCountryFilter] = useState('');

  const currentPage = Math.floor(skip / limit) + 1;
  const totalPages = Math.ceil(total / limit) || 1;

  const handleSearchChange = (e) => {
    const val = e.target.value;
    setSearchText(val);
    onFilterChange({ search: val, classification, country: countryFilter });
  };

  const handleClassificationChange = (e) => {
    const val = e.target.value;
    setClassification(val);
    onFilterChange({ search: searchText, classification: val, country: countryFilter });
  };

  const handleCountryChange = (e) => {
    const val = e.target.value;
    setCountryFilter(val);
    onFilterChange({ search: searchText, classification, country: val });
  };

  const handleExport = (format) => {
    // Build query params
    let url = `${API_BASE}/leads/export?format=${format}`;
    if (activeQueryId) url += `&query_id=${activeQueryId}`;
    if (searchText) url += `&search=${encodeURIComponent(searchText)}`;
    if (classification) url += `&classification=${classification}`;
    if (countryFilter) url += `&country=${encodeURIComponent(countryFilter)}`;

    // Trigger download
    window.open(url, '_blank');
  };

  // Helper to determine custom keys for dynamic modal presentation
  const getCustomKeys = (lead) => {
    if (!lead) return [];
    const standardKeys = [
      'id', 'scrape_job_id', 'company_name', 'website', 'domain', 'description',
      'country', 'address', 'classification', 'industry', 'source', 'contact_page',
      'status', 'created_at', 'emails', 'phones', 'whatsapp', 'linkedin',
      'facebook', 'instagram', 'twitter', 'youtube'
    ];
    return Object.keys(lead).filter(k => !standardKeys.includes(k));
  };

  return (
    <div className="card" style={{ flex: 1 }}>
      <div
        className="card-title"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          borderBottom: 'none',
          paddingBottom: 0
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Globe size={18} className="brand-logo" />
          Discovered Leads ({total} records)
        </span>
        
        {/* Multiformat export triggers */}
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn btn-secondary btn-sm" style={{ width: 'auto', display: 'flex', gap: '0.25rem' }} onClick={() => handleExport('csv')}>
            <Download size={12} />
            CSV
          </button>
          <button className="btn btn-secondary btn-sm" style={{ width: 'auto', display: 'flex', gap: '0.25rem' }} onClick={() => handleExport('xlsx')}>
            <Download size={12} />
            Excel
          </button>
          <button className="btn btn-secondary btn-sm" style={{ width: 'auto', display: 'flex', gap: '0.25rem' }} onClick={() => handleExport('json')}>
            <Download size={12} />
            JSON
          </button>
        </div>
      </div>

      {/* Filter Options */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1rem',
          marginTop: '1.25rem',
          marginBottom: '1.5rem'
        }}
      >
        <input
          type="text"
          className="form-control"
          placeholder="Search by name, domain, industry..."
          value={searchText}
          onChange={handleSearchChange}
        />
        <select
          className="form-control"
          value={classification}
          onChange={handleClassificationChange}
        >
          <option value="">All Classifications</option>
          <option value="manufacturer">Manufacturer</option>
          <option value="distributor">Distributor</option>
          <option value="trader">Trader</option>
          <option value="hospital">Hospital/Clinic</option>
          <option value="restaurant">Restaurant/Eatery</option>
          <option value="tech company">Tech Company</option>
          <option value="startup">Startup</option>
          <option value="logistics company">Logistics Company</option>
          <option value="reseller">Reseller</option>
          <option value="unknown">Unknown Role</option>
        </select>
        <input
          type="text"
          className="form-control"
          placeholder="Filter by country..."
          value={countryFilter}
          onChange={handleCountryChange}
        />
      </div>

      {/* Entity Table Grid */}
      <div className="table-responsive">
        {leads.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            No leads found. Launch a scraper run or adjust your filters.
          </div>
        ) : (
          <table className="lead-table">
            <thead>
              <tr>
                <th>Company Name</th>
                <th>Classification</th>
                <th>Industry</th>
                <th>Country</th>
                <th>Emails</th>
                <th>Phones / WA</th>
                <th style={{ textAlign: 'center' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <tr key={lead.id}>
                  <td style={{ fontWeight: 600 }}>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <span>{lead.company_name || 'N/A'}</span>
                      {lead.website && (
                        <a
                          href={lead.website}
                          target="_blank"
                          rel="noreferrer"
                          style={{
                            fontSize: '0.75rem',
                            color: 'var(--text-secondary)',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.2rem',
                            marginTop: '0.1rem'
                          }}
                        >
                          {lead.domain}
                          <ExternalLink size={10} />
                        </a>
                      )}
                    </div>
                  </td>
                  <td>
                    <span
                      className={`badge badge-${lead.classification}`}
                      style={{
                        backgroundColor:
                          lead.classification === 'manufacturer'
                            ? 'rgba(16, 185, 129, 0.15)'
                            : lead.classification === 'hospital' || lead.classification === 'clinic'
                            ? 'rgba(6, 182, 212, 0.15)'
                            : lead.classification === 'tech company' || lead.classification === 'startup'
                            ? 'rgba(139, 92, 246, 0.15)'
                            : lead.classification === 'restaurant'
                            ? 'rgba(245, 158, 11, 0.15)'
                            : 'rgba(100, 116, 139, 0.15)',
                        color:
                          lead.classification === 'manufacturer'
                            ? 'var(--color-success)'
                            : lead.classification === 'hospital' || lead.classification === 'clinic'
                            ? 'var(--color-info)'
                            : lead.classification === 'tech company' || lead.classification === 'startup'
                            ? 'var(--color-secondary)'
                            : lead.classification === 'restaurant'
                            ? 'var(--color-warning)'
                            : 'var(--text-secondary)',
                        border: '1px solid rgba(255, 255, 255, 0.05)'
                      }}
                    >
                      {lead.classification || 'unknown'}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.85rem' }}>
                      <Briefcase size={12} className="brand-logo" />
                      {lead.industry || 'Other'}
                    </div>
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.85rem' }}>
                      <MapPin size={12} className="brand-logo" />
                      {lead.country || 'Unknown'}
                    </div>
                  </td>
                  <td title={lead.emails || 'N/A'}>
                    <span style={{ fontSize: '0.85rem' }}>
                      {lead.emails ? lead.emails.split(',')[0] : 'N/A'}
                      {lead.emails && lead.emails.split(',').length > 1 && (
                        <span style={{ color: 'var(--color-primary)', fontSize: '0.75rem', marginLeft: '0.25rem' }}>
                          +{lead.emails.split(',').length - 1}
                        </span>
                      )}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontSize: '0.85rem' }}>
                      {lead.phones ? lead.phones.split(',')[0] : lead.whatsapp ? lead.whatsapp.split(',')[0] : 'N/A'}
                      {(lead.phones && lead.phones.split(',').length > 1) || (lead.whatsapp && lead.whatsapp.split(',').length > 1) ? (
                        <span style={{ color: 'var(--color-primary)', fontSize: '0.75rem', marginLeft: '0.25rem' }}>+more</span>
                      ) : null}
                    </span>
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <button
                      className="btn btn-secondary btn-sm"
                      style={{ padding: '0.35rem', borderRadius: '4px', width: 'auto' }}
                      onClick={() => setSelectedLead(lead)}
                    >
                      <Eye size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginTop: '1.5rem',
            paddingTop: '1rem',
            borderTop: '1px solid var(--border-color)'
          }}
        >
          <button
            className="btn btn-secondary btn-sm"
            style={{ width: 'auto' }}
            disabled={currentPage === 1}
            onClick={() => onPageChange(currentPage - 2)}
          >
            Previous
          </button>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Page {currentPage} of {totalPages}
          </span>
          <button
            className="btn btn-secondary btn-sm"
            style={{ width: 'auto' }}
            disabled={currentPage === totalPages}
            onClick={() => onPageChange(currentPage)}
          >
            Next
          </button>
        </div>
      )}

      {/* Dynamic Profile Details Modal */}
      {selectedLead && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Company Lead Intelligence Profile</h3>
              <button
                className="btn btn-secondary btn-sm"
                style={{ padding: '0.25rem', width: 'auto', border: 'none' }}
                onClick={() => setSelectedLead(null)}
              >
                <X size={18} />
              </button>
            </div>
            
            <div className="modal-body">
              <div className="detail-grid">
                
                {/* Standard Sections */}
                <div className="detail-label">Company Name</div>
                <div className="detail-value" style={{ fontWeight: 600, fontSize: '1.1rem' }}>
                  {selectedLead.company_name || 'N/A'}
                </div>

                <div className="detail-label">Website</div>
                <div className="detail-value">
                  {selectedLead.website ? (
                    <a href={selectedLead.website} target="_blank" rel="noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                      {selectedLead.website}
                      <ExternalLink size={12} />
                    </a>
                  ) : (
                    'N/A'
                  )}
                </div>

                <div className="detail-label">Classification</div>
                <div className="detail-value">
                  <span className={`badge badge-${selectedLead.classification}`} style={{ border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                    {selectedLead.classification || 'unknown'}
                  </span>
                </div>

                <div className="detail-label">Industry</div>
                <div className="detail-value">
                  <span className="tag" style={{ backgroundColor: 'rgba(59, 130, 246, 0.1)', color: 'var(--color-primary)' }}>
                    {selectedLead.industry || 'Other'}
                  </span>
                </div>

                {selectedLead.description && (
                  <>
                    <div className="detail-label">Description</div>
                    <div className="detail-value" style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                      {selectedLead.description}
                    </div>
                  </>
                )}

                <div className="detail-label">Emails</div>
                <div className="detail-value">
                  {selectedLead.emails ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                      {selectedLead.emails.split(',').map((e) => (
                        <a key={e} href={`mailto:${e}`}>
                          {e}
                        </a>
                      ))}
                    </div>
                  ) : (
                    'N/A'
                  )}
                </div>

                <div className="detail-label">Phone Numbers</div>
                <div className="detail-value">
                  {selectedLead.phones ? selectedLead.phones.split(',').join(', ') : 'N/A'}
                </div>

                <div className="detail-label">WhatsApp</div>
                <div className="detail-value">
                  {selectedLead.whatsapp ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                      {selectedLead.whatsapp.split(',').map((w) => (
                        <a key={w} href={`https://wa.me/${w}`} target="_blank" rel="noreferrer">
                          +{w}
                        </a>
                      ))}
                    </div>
                  ) : (
                    'N/A'
                  )}
                </div>

                <div className="detail-label">Social Media</div>
                <div className="detail-value" style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
                  {selectedLead.linkedin && <a href={selectedLead.linkedin} target="_blank" rel="noreferrer">LinkedIn</a>}
                  {selectedLead.facebook && <a href={selectedLead.facebook} target="_blank" rel="noreferrer">Facebook</a>}
                  {selectedLead.instagram && <a href={selectedLead.instagram} target="_blank" rel="noreferrer">Instagram</a>}
                  {selectedLead.twitter && <a href={selectedLead.twitter} target="_blank" rel="noreferrer">X (Twitter)</a>}
                  {selectedLead.youtube && <a href={selectedLead.youtube} target="_blank" rel="noreferrer">YouTube</a>}
                  {!selectedLead.linkedin && !selectedLead.facebook && !selectedLead.instagram && !selectedLead.twitter && !selectedLead.youtube && 'None'}
                </div>

                <div className="detail-label">Country</div>
                <div className="detail-value">{selectedLead.country || 'Unknown'}</div>

                <div className="detail-label">Physical Address</div>
                <div className="detail-value">{selectedLead.address || 'N/A'}</div>

                <div className="detail-label">Discovery Source</div>
                <div className="detail-value" style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  {selectedLead.source || 'Search Engine'}
                </div>

                <div className="detail-label">Contact Page</div>
                <div className="detail-value" style={{ fontSize: '0.85rem', wordBreak: 'break-all' }}>
                  {selectedLead.contact_page ? (
                    <a href={selectedLead.contact_page} target="_blank" rel="noreferrer">
                      {selectedLead.contact_page}
                    </a>
                  ) : (
                    'N/A'
                  )}
                </div>

                {/* --- Dynamic Custom Extracted Fields Section --- */}
                {getCustomKeys(selectedLead).length > 0 && (
                  <>
                    <div style={{ gridColumn: 'span 2', borderTop: '1px solid var(--border-color)', margin: '0.5rem 0' }}></div>
                    <div style={{ gridColumn: 'span 2', fontWeight: 600, color: 'var(--color-secondary)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                      <FileText size={14} />
                      AI Extracted Dynamic Fields
                    </div>
                    {getCustomKeys(selectedLead).map((key) => (
                      <React.Fragment key={key}>
                        <div className="detail-label" style={{ textTransform: 'capitalize' }}>
                          {key.replace(/_/g, ' ')}
                        </div>
                        <div className="detail-value" style={{ fontWeight: 500, color: 'var(--color-primary)' }}>
                          {selectedLead[key] !== null && selectedLead[key] !== undefined ? String(selectedLead[key]) : 'N/A'}
                        </div>
                      </React.Fragment>
                    ))}
                  </>
                )}

              </div>
            </div>
            
            <div className="modal-footer">
              <button className="btn btn-secondary" style={{ width: 'auto' }} onClick={() => setSelectedLead(null)}>
                Close Profile
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
