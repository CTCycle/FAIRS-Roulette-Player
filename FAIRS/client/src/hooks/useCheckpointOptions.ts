import { useEffect, useRef, useState } from 'react';

interface UseCheckpointOptionsParams {
    selectedCheckpoint: string;
    onSelectCheckpoint: (checkpoint: string) => void;
}

const normalizeCheckpointList = (payload: unknown): string[] => {
    if (!Array.isArray(payload)) {
        return [];
    }

    return payload.flatMap((entry) => {
        if (typeof entry === 'string') {
            const trimmed = entry.trim();
            return trimmed.length > 0 ? [trimmed] : [];
        }
        if (typeof entry === 'number' && Number.isFinite(entry)) {
            return [String(entry)];
        }
        return [];
    });
};

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

                const normalized = normalizeCheckpointList(data);
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

