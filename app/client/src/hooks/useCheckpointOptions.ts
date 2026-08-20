import { useEffect, useRef, useState } from 'react';
import { fetchTrainingCheckpoints } from '../utils/trainingApi';

interface UseCheckpointOptionsParams {
    selectedCheckpoint: string;
    onSelectCheckpoint: (checkpoint: string) => void;
}

export const useCheckpointOptions = ({
    selectedCheckpoint,
    onSelectCheckpoint,
}: UseCheckpointOptionsParams): string[] => {
    const [checkpoints, setCheckpoints] = useState<string[]>([]);
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

        const loadCheckpoints = async (): Promise<void> => {
            try {
                const normalized = await fetchTrainingCheckpoints();
                if (!mounted) {
                    return;
                }

                setCheckpoints(normalized);

                if (normalized.length > 0 && !latestCheckpointRef.current) {
                    onSelectCheckpointRef.current(normalized[0]);
                }
            } catch (error) {
                console.error('Failed to load checkpoints:', error);
            }
        };

        void loadCheckpoints();

        return () => {
            mounted = false;
        };
    }, []);

    return checkpoints;
};

