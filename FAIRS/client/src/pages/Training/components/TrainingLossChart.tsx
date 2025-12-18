import React, { useMemo } from 'react';

export interface TrainingHistoryPoint {
    time_step: number;
    loss: number;
    rmse: number;
    epoch: number;
}

interface TrainingLossChartProps {
    points: TrainingHistoryPoint[];
}

const buildPath = (points: TrainingHistoryPoint[], xMin: number, xMax: number, yMin: number, yMax: number, width: number, height: number, key: keyof Pick<TrainingHistoryPoint, 'loss' | 'rmse'>) => {
    if (points.length < 2) {
        return '';
    }

    const xSpan = Math.max(1, xMax - xMin);
    const ySpan = Math.max(1e-9, yMax - yMin);

    const toX = (timeStep: number) => ((timeStep - xMin) / xSpan) * width;
    const toY = (value: number) => height - ((value - yMin) / ySpan) * height;

    return points.reduce((path, point, index) => {
        const x = toX(point.time_step);
        const y = toY(Number(point[key]));
        const command = index === 0 ? 'M' : 'L';
        return `${path}${command} ${x.toFixed(2)} ${y.toFixed(2)} `;
    }, '');
};

export const TrainingLossChart: React.FC<TrainingLossChartProps> = ({ points }) => {
    const viewWidth = 860;
    const viewHeight = 260;

    const { lossPath, rmsePath, yMin, yMax, xMin, xMax } = useMemo(() => {
        if (points.length === 0) {
            return { lossPath: '', rmsePath: '', yMin: 0, yMax: 1, xMin: 0, xMax: 1 };
        }

        const xMinValue = points[0].time_step;
        const xMaxValue = points[points.length - 1].time_step;
        const numericValues = points.flatMap((point) => [point.loss, point.rmse]).filter((value) => Number.isFinite(value));
        const rawMin = numericValues.length ? Math.min(...numericValues) : 0;
        const rawMax = numericValues.length ? Math.max(...numericValues) : 1;
        const padding = (rawMax - rawMin) * 0.1 || 1;
        const yMinValue = rawMin - padding;
        const yMaxValue = rawMax + padding;

        return {
            lossPath: buildPath(points, xMinValue, xMaxValue, yMinValue, yMaxValue, viewWidth, viewHeight, 'loss'),
            rmsePath: buildPath(points, xMinValue, xMaxValue, yMinValue, yMaxValue, viewWidth, viewHeight, 'rmse'),
            yMin: yMinValue,
            yMax: yMaxValue,
            xMin: xMinValue,
            xMax: xMaxValue,
        };
    }, [points]);

    if (points.length < 2) {
        return (
            <div className="training-chart-empty">
                Waiting for training data...
            </div>
        );
    }

    const gridLines = 4;
    const grid = Array.from({ length: gridLines + 1 }, (_, index) => {
        const y = (viewHeight / gridLines) * index;
        const value = yMax - ((y / viewHeight) * (yMax - yMin));
        return { y, value };
    });

    return (
        <svg
            className="training-chart"
            viewBox={`0 0 ${viewWidth} ${viewHeight}`}
            preserveAspectRatio="none"
            role="img"
            aria-label={`Training loss chart from step ${xMin} to ${xMax}`}
        >
            <rect x="0" y="0" width={viewWidth} height={viewHeight} fill="rgba(255, 255, 255, 0.02)" />
            {grid.map((line) => (
                <g key={line.y}>
                    <line x1="0" y1={line.y} x2={viewWidth} y2={line.y} stroke="rgba(255, 255, 255, 0.08)" strokeWidth="1" />
                    <text x="8" y={Math.max(12, line.y - 4)} fill="rgba(255, 255, 255, 0.55)" fontSize="11">
                        {line.value.toFixed(3)}
                    </text>
                </g>
            ))}
            <path d={lossPath} fill="none" stroke="#f87171" strokeWidth="2.2" />
            <path d={rmsePath} fill="none" stroke="#fbbf24" strokeWidth="2.2" />
        </svg>
    );
};

