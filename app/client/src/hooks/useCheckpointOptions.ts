import { useEffect, useRef, useState } from 'react';
import { fetchTrainingCheckpoints } from '../utils/trainingApi';
import { isAbortError } from '../utils/apiClient';

interface UseCheckpointOptionsParams {
    selectedCheckpoint: string;
    onSelectCheckpoint: (checkpoint: string) => void;
}

interface UseCheckpointOptionsResult {
    checkpoints: string[];
    isLoading: boolean;
}

export const useCheckpointOptions = ({
    selectedCheckpoint,
    onSelectCheckpoint,
}: UseCheckpointOptionsParams): UseCheckpointOptionsResult => {
    const [checkpoints, setCheckpoints] = useState<string[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const latestCheckpointRef = useRef(selectedCheckpoint);
    const onSelectCheckpointRef = useRef(onSelectCheckpoint);

    useEffect(() => {
        latestCheckpointRef.current = selectedCheckpoint;
    }, [selectedCheckpoint]);

    useEffect(() => {
        onSelectCheckpointRef.current = onSelectCheckpoint;
    }, [onSelectCheckpoint]);

    useEffect(() => {
        let mounted = true;
        const controller = new AbortController();

        const loadCheckpoints = async (): Promise<void> => {
            try {
                const normalized = await fetchTrainingCheckpoints(controller.signal);
                if (!mounted) {
                    return;
                }

                setCheckpoints(normalized);

                if (normalized.length > 0 && !latestCheckpointRef.current) {
                    onSelectCheckpointRef.current(normalized[0]);
                }
            } catch (error) {
                if (!isAbortError(error)) {
                    console.error('Failed to load checkpoints:', error);
                }
            } finally {
                if (mounted) {
                    setIsLoading(false);
                }
            }
        };

        void loadCheckpoints();

        return () => {
            mounted = false;
            controller.abort();
        };
    }, []);

    return { checkpoints, isLoading };
};

