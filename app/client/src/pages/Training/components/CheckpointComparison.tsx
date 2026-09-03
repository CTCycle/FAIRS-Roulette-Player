import React, { useEffect, useMemo, useRef, useState } from 'react';
import { GitCompareArrows } from 'lucide-react';

import type { CheckpointMetadataResponse } from '../../../types/frontendApi';
import { isAbortError } from '../../../utils/apiClient';
import {
    fetchCheckpointMetadata,
    fetchTrainingCheckpoints,
} from '../../../utils/trainingApi';
import './CheckpointComparison.css';

const COMPARISON_FIELDS = [
    ['Dataset ID', 'dataset_id'],
    ['Episodes', 'episodes'],
    ['Batch Size', 'batch_size'],
    ['Learning Rate', 'learning_rate'],
    ['Perceptive Field', 'perceptive_field_size'],
    ['QNet Neurons', 'neurons'],
    ['Embedding Dims', 'embedding_dimensions'],
    ['Exploration Rate', 'exploration_rate'],
    ['Exploration Decay', 'exploration_rate_decay'],
    ['Discount Rate', 'discount_rate'],
    ['Final Loss', 'final_loss'],
    ['Final RMSE', 'final_rmse'],
    ['Validation Loss', 'final_val_loss'],
    ['Validation RMSE', 'final_val_rmse'],
] as const;

const formatValue = (value: unknown): string => {
    if (value === null || value === undefined || value === '') {
        return 'N/A';
    }
    if (typeof value === 'number') {
        return Number.isFinite(value) ? value.toLocaleString(undefined, { maximumFractionDigits: 6 }) : 'N/A';
    }
    return String(value);
};

export const CheckpointComparison: React.FC = () => {
    const [checkpoints, setCheckpoints] = useState<string[]>([]);
    const [leftCheckpoint, setLeftCheckpoint] = useState('');
    const [rightCheckpoint, setRightCheckpoint] = useState('');
    const [metadata, setMetadata] = useState<Record<string, CheckpointMetadataResponse>>({});
    const [error, setError] = useState<string | null>(null);
    const mountedRef = useRef(true);

    useEffect(() => {
        mountedRef.current = true;
        const controller = new AbortController();
        const load = async () => {
            try {
                const values = await fetchTrainingCheckpoints(controller.signal);
                if (!mountedRef.current) {
                    return;
                }
                setCheckpoints(values);
                setLeftCheckpoint(values[0] ?? '');
                setRightCheckpoint(values[1] ?? values[0] ?? '');
            } catch (loadError) {
                if (!isAbortError(loadError) && mountedRef.current) {
                    setError('Unable to load checkpoints for comparison.');
                }
            }
        };
        void load();
        return () => {
            mountedRef.current = false;
            controller.abort();
        };
    }, []);

    useEffect(() => {
        const selected = Array.from(new Set([leftCheckpoint, rightCheckpoint].filter(Boolean)));
        const missing = selected.filter((checkpoint) => !metadata[checkpoint]);
        if (missing.length === 0) {
            return;
        }
        const controller = new AbortController();
        const load = async () => {
            try {
                const results = await Promise.all(
                    missing.map(async (checkpoint) => [
                        checkpoint,
                        await fetchCheckpointMetadata(checkpoint, controller.signal),
                    ] as const),
                );
                if (mountedRef.current) {
                    setMetadata((current) => ({ ...current, ...Object.fromEntries(results) }));
                    setError(null);
                }
            } catch (loadError) {
                if (!isAbortError(loadError) && mountedRef.current) {
                    setError('Unable to load checkpoint metadata for comparison.');
                }
            }
        };
        void load();
        return () => controller.abort();
    }, [leftCheckpoint, metadata, rightCheckpoint]);

    const comparisonRows = useMemo(() => {
        const leftSummary = leftCheckpoint ? metadata[leftCheckpoint]?.summary : undefined;
        const rightSummary = rightCheckpoint ? metadata[rightCheckpoint]?.summary : undefined;
        return COMPARISON_FIELDS.map(([label, key]) => ({
            label,
            left: formatValue(leftSummary?.[key]),
            right: formatValue(rightSummary?.[key]),
        }));
    }, [leftCheckpoint, metadata, rightCheckpoint]);

    if (checkpoints.length < 2) {
        return null;
    }

    return (
        <section className="checkpoint-comparison" aria-labelledby="checkpoint-comparison-title">
            <div className="checkpoint-comparison-header">
                <div>
                    <h3 id="checkpoint-comparison-title"><GitCompareArrows size={18} /> Compare Checkpoints</h3>
                    <p>Compare configuration and stored training summaries. These values are not a standardized benchmark.</p>
                </div>
            </div>

            <div className="checkpoint-comparison-selectors">
                <label>
                    Checkpoint A
                    <select value={leftCheckpoint} onChange={(event) => setLeftCheckpoint(event.target.value)}>
                        {checkpoints.map((checkpoint) => <option key={checkpoint} value={checkpoint}>{checkpoint}</option>)}
                    </select>
                </label>
                <label>
                    Checkpoint B
                    <select value={rightCheckpoint} onChange={(event) => setRightCheckpoint(event.target.value)}>
                        {checkpoints.map((checkpoint) => <option key={checkpoint} value={checkpoint}>{checkpoint}</option>)}
                    </select>
                </label>
            </div>

            {error && <div className="checkpoint-comparison-error" role="alert">{error}</div>}

            <div className="checkpoint-comparison-table-wrap">
                <table className="checkpoint-comparison-table">
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>{leftCheckpoint}</th>
                            <th>{rightCheckpoint}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {comparisonRows.map((row) => (
                            <tr key={row.label}>
                                <td>{row.label}</td>
                                <td>{row.left}</td>
                                <td>{row.right}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </section>
    );
};
