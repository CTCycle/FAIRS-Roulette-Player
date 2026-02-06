import React, { useMemo } from 'react';

export interface TrainingHistoryPoint {
    time_step: number;
    loss: number;
    rmse: number;
    epoch: number;
    val_loss?: number;
    val_rmse?: number;
    reward?: number;
    total_reward?: number;
    capital?: number;
    capital_gain?: number;
}

interface TrainingLossChartProps {
    points: TrainingHistoryPoint[];
    maxSteps?: number;
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
    offsetLeft: number = 0,
    offsetTop: number = 0
) => {
    if (points.length < 2) {
        return '';
    }

    const xSpan = Math.max(1, xMax - xMin);
    const ySpan = Math.max(1e-9, yMax - yMin);

    const toX = (timeStep: number) => offsetLeft + ((timeStep - xMin) / xSpan) * width;
    const toY = (value: number) => offsetTop + (height - ((value - yMin) / ySpan) * height);

    return points.reduce((path, point, index) => {
        const val = point[key];
        if (typeof val !== 'number') return path;

        const x = toX(point.time_step);
        const y = toY(val);
        const command = (index === 0 || path === '') ? 'M' : 'L';
        return `${path}${command} ${x.toFixed(2)} ${y.toFixed(2)} `;
    }, '');
};

/**
 * TrainingLossChart - Displays Loss metrics (training + validation)
 * Shows loss (solid red) and val_loss (dashed red) lines
 */
export const TrainingLossChart: React.FC<TrainingLossChartProps> = ({ points, maxSteps }) => {
    const viewWidth = 420;
    const viewHeight = 220;
    const padding = { left: 50, right: 12, top: 12, bottom: 26 };
    const plotWidth = viewWidth - padding.left - padding.right;
    const plotHeight = viewHeight - padding.top - padding.bottom;

    const { lossPath, valLossPath, yMin, yMax, xMin, xMax } = useMemo(() => {
        if (points.length === 0) {
            return { lossPath: '', valLossPath: '', yMin: 0, yMax: 1, xMin: 0, xMax: 1 };
        }

        const xMinValue = points[0].time_step;
        const xMaxValue = points[points.length - 1].time_step;
        
        // Only use loss values for Y-axis scaling
        const lossValues = points.flatMap((point) => {
            const vals = [point.loss];
            if (point.val_loss !== undefined) vals.push(point.val_loss);
            return vals;
        }).filter((value) => Number.isFinite(value));
        
        const rawMin = lossValues.length ? Math.min(...lossValues) : 0;
        const rawMax = lossValues.length ? Math.max(...lossValues) : 1;
        const yPadding = (rawMax - rawMin) * 0.1 || 1;
        const yMinValue = rawMin - yPadding;
        const yMaxValue = rawMax + yPadding;

        return {
            lossPath: buildPath(points, xMinValue, xMaxValue, yMinValue, yMaxValue, plotWidth, plotHeight, 'loss', padding.left, padding.top),
            valLossPath: buildPath(points, xMinValue, xMaxValue, yMinValue, yMaxValue, plotWidth, plotHeight, 'val_loss', padding.left, padding.top),
            yMin: yMinValue,
            yMax: yMaxValue,
            xMin: xMinValue,
            xMax: xMaxValue,
        };
    }, [points, plotHeight, plotWidth, padding.left, padding.top]);

    const gridLines = 4;
    const grid = Array.from({ length: gridLines + 1 }, (_, index) => {
        const y = padding.top + (plotHeight / gridLines) * index;
        const value = yMax - ((index / gridLines) * (yMax - yMin));
        return { y, value };
    });

    const tickCount: number = 5;
    const xTicks = Array.from({ length: tickCount }, (_, index) => {
        const ratio = tickCount === 1 ? 0 : index / (tickCount - 1);
        const value = xMin + ratio * (xMax - xMin);
        const x = padding.left + ratio * plotWidth;
        return { x, value };
    });

    const episodeBoundaries = useMemo(() => {
        if (points.length < 2 || !maxSteps || maxSteps <= 0) {
            return [];
        }
        const episodes = Array.from(new Set(points.map((point) => point.epoch)))
            .filter((epoch) => typeof epoch === 'number' && epoch > 1)
            .sort((a, b) => a - b);
        return episodes.map((episode) => (episode - 1) * maxSteps)
            .filter((step) => step >= xMin && step <= xMax);
    }, [maxSteps, points, xMax, xMin]);

    if (points.length < 2) {
        return (
            <div className="training-chart-empty">
                Waiting for training data...
            </div>
        );
    }

    return (
        <svg
            className="training-chart"
            viewBox={`0 0 ${viewWidth} ${viewHeight}`}
            preserveAspectRatio="none"
            role="img"
            aria-label={`Training loss chart from step ${Math.round(xMin)} to ${Math.round(xMax)}`}
        >
            <rect x="0" y="0" width={viewWidth} height={viewHeight} fill="var(--chart-bg)" />
            {grid.map((line) => (
                <g key={line.y}>
                    <line x1={lossPath ? padding.left : 0} y1={line.y} x2={viewWidth} y2={line.y} stroke="var(--chart-grid)" strokeWidth="1" />
                    <text x="0" y={Math.max(12, line.y - 4)} fill="var(--chart-text)" fontSize="10" textAnchor="start">
                        {line.value.toFixed(3)}
                    </text>
                </g>
            ))}
            {episodeBoundaries.map((step) => {
                const xSpan = Math.max(1, xMax - xMin);
                const x = padding.left + ((step - xMin) / xSpan) * plotWidth;
                return (
                    <line
                        key={`episode-${step}`}
                        x1={x}
                        y1={padding.top}
                        x2={x}
                        y2={padding.top + plotHeight}
                        stroke="var(--chart-grid)"
                        strokeWidth="1"
                        strokeDasharray="4 4"
                    />
                );
            })}
            <line
                x1={padding.left}
                y1={padding.top + plotHeight}
                x2={padding.left + plotWidth}
                y2={padding.top + plotHeight}
                stroke="var(--chart-grid)"
                strokeWidth="1"
            />
            {xTicks.map((tick) => (
                <g key={tick.x}>
                    <line
                        x1={tick.x}
                        y1={padding.top + plotHeight}
                        x2={tick.x}
                        y2={padding.top + plotHeight + 4}
                        stroke="var(--chart-grid)"
                        strokeWidth="1"
                    />
                    <text
                        x={tick.x}
                        y={viewHeight - 6}
                        fill="var(--chart-text)"
                        fontSize="10"
                        textAnchor="middle"
                    >
                        {Math.round(tick.value)}
                    </text>
                </g>
            ))}
            {/* Training Loss Curve (solid) */}
            <path d={lossPath} fill="none" stroke="var(--chart-loss)" strokeWidth="2.2" />
            {/* Validation Loss Curve (dashed) */}
            <path d={valLossPath} fill="none" stroke="var(--chart-loss-val)" strokeWidth="2" strokeDasharray="4 4" strokeOpacity="0.8" />
        </svg>
    );
};
