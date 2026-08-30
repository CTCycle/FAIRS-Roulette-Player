import { useEffect, useMemo, useRef, useState } from 'react';
import type { InferenceSetupState } from '../types/inference';
import { useCheckpointOptions } from './useCheckpointOptions';
import {
    parseCheckpointOptionMetadata,
} from '../utils/frontendApiParsers';
import type { CheckpointOptionMetadata } from '../types/frontendApi';
import {
    fetchCheckpointMetadata,
    fetchTrainingDatasetSummaries,
} from '../utils/trainingApi';

export interface InferenceDatasetOption {
    dataset_id: number;
    dataset_name: string;
    row_count: number;
}

interface UseInferenceSetupOptionsParams {
    setup: InferenceSetupState;
    onSetupChange: (updates: Partial<InferenceSetupState>) => void;
}

interface UseInferenceSetupOptionsResult {
    checkpoints: string[];
    datasets: InferenceDatasetOption[];
    checkpointMetadataMap: Record<string, CheckpointOptionMetadata>;
    selectedCheckpointMetadata: CheckpointOptionMetadata | undefined;
    selectedDatasetIsCompatible: boolean;
}

export const useInferenceSetupOptions = ({
    setup,
    onSetupChange,
}: UseInferenceSetupOptionsParams): UseInferenceSetupOptionsResult => {
    const onSetupChangeRef = useRef(onSetupChange);
    const latestSetupRef = useRef(setup);
    const checkpoints = useCheckpointOptions({
        selectedCheckpoint: setup.checkpoint,
        onSelectCheckpoint: (nextCheckpoint) => onSetupChange({ checkpoint: nextCheckpoint }),
    });
    const [datasets, setDatasets] = useState<InferenceDatasetOption[]>([]);
    const [checkpointMetadataMap, setCheckpointMetadataMap] = useState<Record<string, CheckpointOptionMetadata>>({});

    useEffect(() => {
        latestSetupRef.current = setup;
    }, [setup]);

    useEffect(() => {
        onSetupChangeRef.current = onSetupChange;
    }, [onSetupChange]);

    useEffect(() => {
        const loadDatasets = async () => {
            try {
                const values = (await fetchTrainingDatasetSummaries()).map((entry) => ({
                    dataset_id: entry.datasetId,
                    dataset_name: entry.datasetName,
                    row_count: entry.rowCount,
                }));

                setDatasets(values);
                if (values.length > 0 && latestSetupRef.current.selectedDataset === null) {
                    onSetupChangeRef.current({
                        selectedDataset: values[0].dataset_id,
                    });
                }
            } catch (err) {
                console.error('Failed to load datasets:', err);
            }
        };

        void loadDatasets();
    }, []);

    useEffect(() => {
        if (checkpoints.length === 0) {
            return;
        }

        let mounted = true;

        const loadCheckpointMetadata = async () => {
            try {
                const entries = await Promise.all(
                    checkpoints.map(async (checkpoint) => {
                        const metadata = await fetchCheckpointMetadata(checkpoint);
                        return [checkpoint, parseCheckpointOptionMetadata(metadata.summary)] as const;
                    }),
                );

                if (!mounted) {
                    return;
                }

                setCheckpointMetadataMap(Object.fromEntries(entries));
            } catch (error) {
                if (mounted) {
                    setCheckpointMetadataMap({});
                }
                console.error('Failed to load checkpoint metadata:', error);
            }
        };

        void loadCheckpointMetadata();

        return () => {
            mounted = false;
        };
    }, [checkpoints]);

    const selectedCheckpointMetadata = setup.checkpoint
        ? checkpointMetadataMap[setup.checkpoint]
        : undefined;

    const selectedDatasetIsCompatible = useMemo(() => {
        if (setup.uploadedDatasetId !== null) {
            return true;
        }
        if (setup.selectedDataset === null) {
            return false;
        }
        const dataset = datasets.find((entry) => entry.dataset_id === setup.selectedDataset);
        if (!dataset) {
            return false;
        }
        const requiredRows = selectedCheckpointMetadata?.perceptiveFieldSize;
        return requiredRows === null
            || requiredRows === undefined
            || dataset.row_count >= requiredRows;
    }, [datasets, selectedCheckpointMetadata, setup.selectedDataset, setup.uploadedDatasetId]);

    useEffect(() => {
        if (datasets.length === 0 || checkpoints.length === 0 || setup.uploadedDatasetId !== null) {
            return;
        }

        const getCompatibleDataset = (checkpointName: string): InferenceDatasetOption | undefined => {
            const metadata = checkpointMetadataMap[checkpointName];
            const preferredDataset = metadata?.datasetId !== null && metadata?.datasetId !== undefined
                ? datasets.find((dataset) => dataset.dataset_id === metadata.datasetId)
                : undefined;
            const requiredRows = metadata?.perceptiveFieldSize;
            const isCompatible = (dataset: InferenceDatasetOption) => (
                requiredRows === null
                || requiredRows === undefined
                || dataset.row_count >= requiredRows
            );

            if (preferredDataset && isCompatible(preferredDataset)) {
                return preferredDataset;
            }

            return datasets.find(isCompatible);
        };

        const currentCheckpoint = checkpoints.includes(setup.checkpoint) ? setup.checkpoint : '';
        const resolvedCheckpoint = currentCheckpoint || (
            checkpoints.find((checkpoint) => Boolean(getCompatibleDataset(checkpoint)))
            ?? checkpoints[0]
        );
        const compatibleDataset = getCompatibleDataset(resolvedCheckpoint);
        const updates: Partial<InferenceSetupState> = {};

        if (resolvedCheckpoint && resolvedCheckpoint !== setup.checkpoint) {
            updates.checkpoint = resolvedCheckpoint;
        }

        if (setup.selectedDataset === null || !selectedDatasetIsCompatible) {
            if (compatibleDataset) {
                updates.selectedDataset = compatibleDataset.dataset_id;
            }
        }

        if (Object.keys(updates).length > 0) {
            onSetupChangeRef.current(updates);
        }
    }, [
        checkpointMetadataMap,
        checkpoints,
        datasets,
        selectedDatasetIsCompatible,
        setup.checkpoint,
        setup.selectedDataset,
        setup.uploadedDatasetId,
    ]);

    return {
        checkpoints,
        datasets,
        checkpointMetadataMap,
        selectedCheckpointMetadata,
        selectedDatasetIsCompatible,
    };
};
