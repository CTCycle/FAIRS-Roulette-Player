import { useEffect, useRef, useState } from 'react';
import { parseCheckpointList } from '../utils/frontendApiParsers';

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
                const response = await fetch('/api/training/checkpoints');
                if (!response.ok) {
                    return;
                }

                const data = await response.json();
                if (!mounted) {
                    return;
                }

                const normalized = parseCheckpointList(data);
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

