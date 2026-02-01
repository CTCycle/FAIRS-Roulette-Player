import React, { useEffect, useState } from 'react';
import { Database, Play, X } from 'lucide-react';
import { useAppState } from '../../../context/AppStateContext';
import { buildTrainingPayload } from './trainingPayload';

interface DatasetPreviewProps {
    refreshKey: number;
    onDelete?: () => void;
}

interface DatasetSummary {
    name: string;
    rowCount: number | null;
}

export const DatasetPreview: React.FC<DatasetPreviewProps> = ({
    refreshKey,
    onDelete,
}) => {
    const { state, dispatch } = useAppState();
    const { newConfig, isTraining } = state.training;
    const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const loadDatasets = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch('/api/database/roulette-series/datasets/summary');
            if (!response.ok) {
                throw new Error('Failed to load dataset summary');
            }
            const data = await response.json();
            const datasetList = Array.isArray(data?.datasets)
                ? data.datasets
                    .filter((entry: unknown) => typeof entry === 'object' && entry !== null)
                    .map((entry: { dataset_name?: unknown; row_count?: unknown }) => ({
                        name: typeof entry.dataset_name === 'string' ? entry.dataset_name : '',
                        rowCount: typeof entry.row_count === 'number' ? entry.row_count : null,
                    }))
                    .filter((entry: DatasetSummary) => entry.name.trim().length > 0)
                : [];
            setDatasets(datasetList);
        } catch (err) {
            try {
                const fallbackResponse = await fetch('/api/database/roulette-series/datasets');
                if (!fallbackResponse.ok) {
                    throw new Error('Failed to load datasets');
                }
                const fallbackData = await fallbackResponse.json();
                const fallbackList = Array.isArray(fallbackData?.datasets)
                    ? fallbackData.datasets
                        .filter((name: unknown) => typeof name === 'string' && name.trim().length > 0)
                        .map((name: string) => ({ name, rowCount: null }))
                    : [];
                setDatasets(fallbackList);
                setError(null);
            } catch (fallbackError) {
                setError('Unable to load datasets.');
                setDatasets([]);
            }
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

    const handleStartTraining = async (datasetName: string) => {
        if (isTraining) {
            alert('Training is already in progress.');
            return;
        }

        const config = buildTrainingPayload(newConfig, datasetName);

        try {
            const response = await fetch('/api/training/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config),
            });

            if (!response.ok) {
                const errorPayload = await response.json();
                alert(`Failed to start training: ${errorPayload.detail || 'Unknown error'}`);
                return;
            }

            dispatch({ type: 'SET_TRAINING_IS_TRAINING', payload: true });
        } catch (err) {
            alert('Failed to connect to training server');
        }
    };

    const formatRowCount = (rowCount: number | null) => {
        if (rowCount === null) {
            return 'Rows: --';
        }
        return `${rowCount.toLocaleString()} rows`;
    };

    return (
        <div className="dataset-preview">
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
                        {datasets.slice(0, 6).map((dataset) => (
                            <div key={dataset.name} className="preview-row">
                                <span className="preview-row-name">{dataset.name}</span>
                                <span className="preview-row-spacer" />
                                <span className="preview-row-count">{formatRowCount(dataset.rowCount)}</span>
                                <button
                                    className="preview-row-icon preview-row-icon-start"
                                    onClick={() => handleStartTraining(dataset.name)}
                                    title="Start training with this dataset"
                                    disabled={isTraining}
                                >
                                    <Play size={16} />
                                </button>
                                <button
                                    className="preview-row-delete"
                                    onClick={() => handleDelete(dataset.name)}
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
