import React, { useState } from 'react';
import { Search, Play, Plus, X, Globe, Cpu, Settings } from 'lucide-react';

const COMMON_FIELDS = [
  { id: 'emails', label: 'Emails' },
  { id: 'phones', label: 'Phones' },
  { id: 'whatsapp', label: 'WhatsApp' },
  { id: 'address', label: 'Address' },
  { id: 'linkedin', label: 'LinkedIn' },
  { id: 'facebook', label: 'Facebook' },
  { id: 'instagram', label: 'Instagram' },
  { id: 'twitter', label: 'X (Twitter)' },
  { id: 'youtube', label: 'YouTube' },
  { id: 'description', label: 'Description' }
];

export default function SearchForm({ onSearchSubmit, isRunning, isStarting }) {
  const isDisabled = isRunning || isStarting;
  const [query, setQuery] = useState('packaging suppliers');
  
  // Country tag manager states
  const [countries, setCountries] = useState(['Germany', 'Mexico']);
  const [countryInput, setCountryInput] = useState('');
  
  // Custom schema fields states
  const [selectedFields, setSelectedFields] = useState(['emails', 'phones', 'whatsapp', 'linkedin', 'address']);
  const [customFields, setCustomFields] = useState(['CEO', 'revenue']);
  const [newFieldInput, setNewFieldInput] = useState('');
  
  // Scraping depth / options states
  const [maxPages, setMaxPages] = useState(2);
  const [concurrency, setConcurrency] = useState(5);
  const [exportFormat, setExportFormat] = useState('csv');

  // Country tags logic
  const handleCountryKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const val = countryInput.trim();
      if (val && !countries.includes(val)) {
        setCountries([...countries, val]);
      }
      setCountryInput('');
    }
  };

  const removeCountryTag = (cToRemove) => {
    setCountries(countries.filter(c => c !== cToRemove));
  };

  // Field checkbox selection logic
  const toggleField = (id) => {
    if (selectedFields.includes(id)) {
      setSelectedFields(selectedFields.filter(f => f !== id));
    } else {
      setSelectedFields([...selectedFields, id]);
    }
  };

  // Custom schema field creation
  const handleAddCustomField = (e) => {
    e.preventDefault();
    const formatted = newFieldInput.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_');
    if (formatted && !customFields.includes(formatted) && !selectedFields.includes(formatted)) {
      setCustomFields([...customFields, formatted]);
    }
    setNewFieldInput('');
  };

  const removeCustomField = (fToRemove) => {
    setCustomFields(customFields.filter(f => f !== fToRemove));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (isDisabled) return;

    // Combine standard fields + custom fields
    const allFields = ['company_name', 'website', ...selectedFields, ...customFields];

    onSearchSubmit({
      keyword: query,
      countries: countries.length > 0 ? countries : null,
      fields: allFields,
      max_pages: parseInt(maxPages) || 1,
      concurrency: parseInt(concurrency) || 5,
      export_format: exportFormat
    });
  };

  return (
    <div className="card">
      <h2 className="card-title">
        <Search size={18} className="brand-logo" />
        New Scraping Job
      </h2>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        
        {/* Topic Input */}
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label htmlFor="query">Query Topic / Industry</label>
          <input
            id="query"
            type="text"
            className="form-control"
            placeholder="e.g. footwear manufacturers, startups, hospitals"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            required
            disabled={isDisabled}
          />
        </div>

        {/* Countries Tags Input */}
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label htmlFor="countries">Target Country (Type name and press Enter)</label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginBottom: '0.4rem' }}>
            {countries.map(c => (
              <span key={c} className="tag" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                {c}
                {!isDisabled && <X size={12} style={{ cursor: 'pointer' }} onClick={() => removeCountryTag(c)} />}
              </span>
            ))}
            {countries.length === 0 && <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Global (All Countries)</span>}
          </div>
          <input
            id="countries"
            type="text"
            className="form-control"
            placeholder="e.g. Germany, USA, Singapore"
            value={countryInput}
            onChange={(e) => setCountryInput(e.target.value)}
            onKeyDown={handleCountryKeyDown}
            disabled={isDisabled}
          />
        </div>

        {/* Dynamic Fields Checklist */}
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label>Standard Fields to Extract</label>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.4rem', marginTop: '0.2rem' }}>
            {COMMON_FIELDS.map(field => (
              <label key={field.id} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={selectedFields.includes(field.id)}
                  onChange={() => toggleField(field.id)}
                  disabled={isDisabled}
                  style={{ accentColor: 'var(--color-primary)' }}
                />
                {field.label}
              </label>
            ))}
          </div>
        </div>

        {/* AI Custom Extracted Fields */}
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label htmlFor="custom-fields">Custom AI Extracted Fields</label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginBottom: '0.4rem' }}>
            {customFields.map(f => (
              <span key={f} className="tag" style={{ backgroundColor: 'rgba(139, 92, 246, 0.1)', borderColor: 'rgba(139, 92, 246, 0.2)', color: 'var(--color-secondary)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                {f}
                {!isDisabled && <X size={12} style={{ cursor: 'pointer' }} onClick={() => removeCustomField(f)} />}
              </span>
            ))}
            {customFields.length === 0 && <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>None (Standard data only)</span>}
          </div>
          
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <input
              id="custom-fields"
              type="text"
              className="form-control"
              style={{ flex: 1 }}
              placeholder="e.g. CEO, founder_name, funding, employees"
              value={newFieldInput}
              onChange={(e) => setNewFieldInput(e.target.value)}
              disabled={isDisabled}
            />
            <button
              type="button"
              className="btn btn-secondary"
              style={{ width: 'auto', padding: '0.5rem 0.75rem' }}
              onClick={handleAddCustomField}
              disabled={isDisabled}
            >
              <Plus size={16} />
            </button>
          </div>
        </div>

        {/* Search settings collapsible grid */}
        <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          
          {/* Depth and Concurrency */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="max-pages">Max Search Pages</label>
              <select
                id="max-pages"
                className="form-control"
                value={maxPages}
                onChange={(e) => setMaxPages(e.target.value)}
                disabled={isDisabled}
              >
                <option value={1}>1 Page</option>
                <option value={2}>2 Pages</option>
                <option value={3}>3 Pages</option>
                <option value={5}>5 Pages</option>
                <option value={10}>10 Pages</option>
              </select>
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="concurrency">Concurrency Limit</label>
              <select
                id="concurrency"
                className="form-control"
                value={concurrency}
                onChange={(e) => setConcurrency(e.target.value)}
                disabled={isDisabled}
              >
                <option value={2}>2 Crawlers</option>
                <option value={5}>5 Crawlers</option>
                <option value={10}>10 Crawlers</option>
                <option value={20}>20 Crawlers</option>
              </select>
            </div>
          </div>

          {/* Export Format */}
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label htmlFor="export-format">Default Export Format</label>
            <select
              id="export-format"
              className="form-control"
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value)}
              disabled={isDisabled}
            >
              <option value="csv">CSV Sheet</option>
              <option value="json">JSON Documents</option>
              <option value="xlsx">Excel File (XLSX)</option>
            </select>
          </div>
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          style={{ marginTop: '0.5rem' }}
          disabled={isDisabled}
        >
          {isStarting ? (
            <>
              <span className="badge badge-running spin" style={{ padding: '0.1rem 0.3rem', marginRight: '0.2rem', backgroundColor: 'transparent' }}></span>
              Starting Scraper... (May take a minute)
            </>
          ) : isRunning ? (
            <>
              <span className="badge badge-running spin" style={{ padding: '0.1rem 0.3rem', marginRight: '0.2rem', backgroundColor: 'transparent' }}></span>
              Scraping In Progress...
            </>
          ) : (
            <>
              <Play size={16} />
              Launch Scraping Run
            </>
          )}
        </button>
      </form>
    </div>
  );
}
