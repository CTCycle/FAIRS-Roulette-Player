import React, { useMemo } from 'react';

import type { TrainingHistoryPoint } from './TrainingLossChart';

interface TrainingRmseChartProps {
    points: TrainingHistoryPoint[];
}

const buildPath = (
    points: TrainingHistoryPoint[],
    xMin: number,
    xMax: number,
    yMin: number,
    yMax: number,
    width: number,
    height: number,
    key: keyof TrainingHistoryPoint,
    offsetLeft: number = 0
) => {
    if (points.length < 2) {
        return '';
    }

    const xSpan = Math.max(1, xMax - xMin);
    const ySpan = Math.max(1e-9, yMax - yMin);

    const toX = (timeStep: number) => ((timeStep - xMin) / xSpan) * width;
    const toY = (value: number) => height - ((value - yMin) / ySpan) * height;

    return points.reduce((path, point, index) => {
        const val = point[key];
        if (typeof val !== 'number') return path;

        const x = offsetLeft + toX(point.time_step);
        const y = toY(val);
        const command = (index === 0 || path === '') ? 'M' : 'L';
        return `${path}${command} ${x.toFixed(2)} ${y.toFixed(2)} `;
    }, '');
};

/**
 * TrainingRmseChart - Displays RMSE metrics (training + validation)
 * Shows rmse (solid yellow) and val_rmse (dashed yellow) lines
 */
export const TrainingRmseChart: React.FC<TrainingRmseChartProps> = ({ points }) => {
    const viewWidth = 420;
    const viewHeight = 220;

    const { rmsePath, valRmsePath, yMin, yMax, xMin, xMax } = useMemo(() => {
        if (points.length === 0) {
            return { rmsePath: '', valRmsePath: '', yMin: 0, yMax: 1, xMin: 0, xMax: 1 };
        }

        const xMinValue = points[0].time_step;
        const xMaxValue = points[points.length - 1].time_step;

        // Only use RMSE values for Y-axis scaling
        const rmseValues = points.flatMap((point) => {
            const vals = [point.rmse];
            if (point.val_rmse !== undefined) vals.push(point.val_rmse);
            return vals;
        }).filter((value) => Number.isFinite(value));

        const rawMin = rmseValues.length ? Math.min(...rmseValues) : 0;
        const rawMax = rmseValues.length ? Math.max(...rmseValues) : 1;
        const padding = (rawMax - rawMin) * 0.1 || 1;
        const yMinValue = rawMin - padding;
        const yMaxValue = rawMax + padding;
        const offsetLeft = 50;

        return {
            rmsePath: buildPath(points, xMinValue, xMaxValue, yMinValue, yMaxValue, viewWidth - offsetLeft, viewHeight, 'rmse', offsetLeft),
            valRmsePath: buildPath(points, xMinValue, xMaxValue, yMinValue, yMaxValue, viewWidth - offsetLeft, viewHeight, 'val_rmse', offsetLeft),
            yMin: yMinValue,
            yMax: yMaxValue,
            xMin: xMinValue,
            xMax: xMaxValue,
            offsetLeft,
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
            aria-label={`Training RMSE chart from step ${xMin} to ${xMax}`}
        >
            <rect x="0" y="0" width={viewWidth} height={viewHeight} fill="var(--chart-bg)" />
            {grid.map((line) => (
                <g key={line.y}>
                    <line x1={rmsePath ? 50 : 0} y1={line.y} x2={viewWidth} y2={line.y} stroke="var(--chart-grid)" strokeWidth="1" />
                    <text x="0" y={Math.max(12, line.y - 4)} fill="var(--chart-text)" fontSize="10" textAnchor="start">
                        {line.value.toFixed(3)}
                    </text>
                </g>
            ))}
            {/* Training RMSE Curve (solid) */}
            <path d={rmsePath} fill="none" stroke="var(--chart-rmse)" strokeWidth="2.2" />
            {/* Validation RMSE Curve (dashed) */}
            <path d={valRmsePath} fill="none" stroke="var(--chart-rmse-val)" strokeWidth="2" strokeDasharray="4 4" strokeOpacity="0.8" />
        </svg>
    );
};
