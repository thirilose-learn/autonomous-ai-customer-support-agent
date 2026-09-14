import React, { useState, useRef, useEffect } from 'react';

export function PersonaSelector({
  personas = [],
  selectedPersona = null,
  loading = false,
  error = null,
  onSelectPersona = () => {},
}) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);
  const listRef = useRef(null);

  const formatScenario = (scenario) => {
    if (!scenario) return 'Active Customer';
    return scenario
      .replace(/_/g, ' ')
      .toLowerCase()
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  const formatCity = (city) => {
    if (!city) return '';
    return city
      .split(' ')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
      .join(' ');
  };

  // Close dropdown on outside click
  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
    }
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
    };
  }, [isOpen]);

  // Handle keyboard navigation
  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      setIsOpen(false);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (!isOpen) {
        setIsOpen(true);
      } else if (listRef.current) {
        const firstBtn = listRef.current.querySelector('button');
        if (firstBtn) firstBtn.focus();
      }
    }
  };

  const handleItemSelect = (demoCustomerId) => {
    onSelectPersona(demoCustomerId);
    setIsOpen(false);
  };

  const currentLabel = selectedPersona
    ? `${selectedPersona.display_name} — ${formatCity(selectedPersona.customer_city)}, ${selectedPersona.customer_state || 'BR'}`
    : loading
    ? 'Loading accounts...'
    : 'Select Account';

  return (
    <div className="persona-selector-container" ref={containerRef} onKeyDown={handleKeyDown}>
      <button
        type="button"
        className={`persona-chip ${isOpen ? 'active' : ''}`}
        onClick={() => !loading && personas.length > 0 && setIsOpen(!isOpen)}
        disabled={loading || personas.length === 0}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label="Select Demo Customer Account"
        title="Demo Customer Account — Click to switch customer persona"
      >
        <span className="persona-icon" aria-hidden="true">👤</span>
        <span className="persona-label-text">{currentLabel}</span>
        <span className={`persona-chevron ${isOpen ? 'open' : ''}`} aria-hidden="true">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </span>
      </button>

      {isOpen && (
        <div className="persona-menu" role="listbox" ref={listRef} aria-label="Demo Customer Accounts">
          <div className="persona-menu-header">
            <span>Demo Customer Accounts</span>
            <span className="persona-menu-count">{personas.length} Available</span>
          </div>
          <div className="persona-menu-items">
            {personas.map((p) => {
              const isSelected = selectedPersona?.demo_customer_id === p.demo_customer_id;
              return (
                <button
                  key={p.demo_customer_id}
                  type="button"
                  className={`persona-menu-item ${isSelected ? 'selected' : ''}`}
                  onClick={() => handleItemSelect(p.demo_customer_id)}
                  role="option"
                  aria-selected={isSelected}
                >
                  <div className="persona-item-body">
                    <div className="persona-item-title">
                      <strong>{p.display_name}</strong>
                      <span className="persona-item-geo">
                        • {formatCity(p.customer_city)}, {p.customer_state || 'BR'}
                      </span>
                    </div>
                    <div className="persona-item-scenario">
                      {formatScenario(p.primary_scenario)}
                    </div>
                  </div>
                  {isSelected && (
                    <span className="persona-item-check" aria-hidden="true">
                      ✓
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {error && <span className="persona-error-tooltip" title={error}>!</span>}
    </div>
  );
}

export default PersonaSelector;
