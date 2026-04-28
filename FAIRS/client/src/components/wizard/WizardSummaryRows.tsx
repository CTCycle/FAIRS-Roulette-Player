import React from 'react';

export interface WizardSummaryRow {
    label: string;
    value: string | number | boolean | null | undefined;
}

interface WizardSummaryRowsProps {
    rows: WizardSummaryRow[];
}

export const WizardSummaryRows: React.FC<WizardSummaryRowsProps> = ({ rows }) => (
    <div className="wizard-summary">
        {rows.map((row) => (
            <div key={row.label} className="wizard-summary-row">
                <span className="wizard-summary-label">{row.label}</span>
                <span className="wizard-summary-value">
                    {typeof row.value === 'number' ? String(row.value) : String(row.value)}
                </span>
            </div>
        ))}
    </div>
);

