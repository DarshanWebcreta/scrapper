import React from 'react';
import { Users, Mail, Phone, Globe } from 'lucide-react';

export default function DashboardStats({ stats }) {
  const {
    total_leads = 0,
    total_emails = 0,
    total_phones = 0,
    total_searches = 0
  } = stats || {};

  return (
    <div className="grid-stats">
      <div className="card stat-card">
        <div className="stat-icon info">
          <Users size={24} />
        </div>
        <div className="stat-info">
          <div className="stat-value">{total_leads}</div>
          <div className="stat-label">Total Leads Found</div>
        </div>
      </div>

      <div className="card stat-card">
        <div className="stat-icon success">
          <Mail size={24} />
        </div>
        <div className="stat-info">
          <div className="stat-value">{total_emails}</div>
          <div className="stat-label">Emails Extracted</div>
        </div>
      </div>

      <div className="card stat-card">
        <div className="stat-icon warning">
          <Phone size={24} />
        </div>
        <div className="stat-info">
          <div className="stat-value">{total_phones}</div>
          <div className="stat-label">Phones / WhatsApps</div>
        </div>
      </div>

      <div className="card stat-card">
        <div className="stat-icon">
          <Globe size={24} />
        </div>
        <div className="stat-info">
          <div className="stat-value">{total_searches}</div>
          <div className="stat-label">Queries Run</div>
        </div>
      </div>
    </div>
  );
}
