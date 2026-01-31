import React, { useEffect, useState } from 'react';
import { Database, X } from 'lucide-react';

interface DatasetPreviewProps {
    refreshKey: number;
    onDelete?: () => void;
}

export const DatasetPreview: React.FC<DatasetPreviewProps> = ({
    refreshKey,
    onDelete,
}) => {
    const [datasets, setDatasets] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const loadDatasets = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch('/api/database/roulette-series/datasets');
            if (!response.ok) {
                throw new Error('Failed to load datasets');
            }
            const data = await response.json();
            const datasetList = Array.isArray(data?.datasets)
                ? data.datasets.filter((name: unknown) => typeof name === 'string' && name.trim().length > 0)
                : [];
            setDatasets(datasetList);
        } catch (err) {
            setError('Unable to load datasets.');
            setDatasets([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        void loadDatasets();
    }, [refreshKey]);

    const handleDelete = async (datasetName: string) => {
        try {
            const response = await fetch(`/api/database/roulette-series/datasets/${encodeURIComponent(datasetName)}`, {
                method: 'DELETE',
            });
            if (!response.ok) {
                throw new Error('Failed to delete dataset');
            }
            await loadDatasets();
            onDelete?.();
        } catch (err) {
            setError('Failed to delete dataset.');
        }
    };

    return (
        <div className="preview-panel dataset-preview">
            <div className="preview-header">
                <Database size={18} />
                <span>Available Datasets</span>
            </div>
            <div className="preview-content">
                {loading && <div className="preview-loading">Loading...</div>}
                {error && <div className="preview-error">{error}</div>}
                {!loading && !error && datasets.length === 0 && (
                    <div className="preview-empty">No datasets available</div>
                )}
                {!loading && !error && datasets.length > 0 && (
                    <div className="preview-list">
                        {datasets.slice(0, 6).map((name) => (
                            <div key={name} className="preview-row">
                                <span className="preview-row-name">{name}</span>
                                <span className="preview-row-spacer" />
                                <button
                                    className="preview-row-delete"
                                    onClick={() => handleDelete(name)}
                                    title="Remove dataset"
                                >
                                    <X size={16} />
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};
