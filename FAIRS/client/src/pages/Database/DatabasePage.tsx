import React, { useState, useEffect, useCallback, useLayoutEffect, useRef } from 'react';
import { RefreshCw, Database, Table2 } from 'lucide-react';
import { useAppState } from '../../context/AppStateContext';
import './Database.css';

interface TableInfo {
    name: string;
    verbose_name: string;
}

interface TableDataPayload {
    columns: string[];
    rows: Record<string, unknown>[];
    offset: number;
    limit: number;
}

interface TableStatsPayload {
    table_name: string;
    verbose_name: string;
    row_count: number;
    column_count: number;
}

const DatabasePage: React.FC = () => {
    const { state, dispatch } = useAppState();
    const { selectedTable, tableData, tableStats } = state.database;

    const [tables, setTables] = useState<TableInfo[]>([]);
    const [isLoadingTables, setIsLoadingTables] = useState(false);
    const [isLoadingData, setIsLoadingData] = useState(false);
    const [isLoadingMore, setIsLoadingMore] = useState(false);
    const [tablesError, setTablesError] = useState<string | null>(null);
    const [dataError, setDataError] = useState<string | null>(null);
    const [loadMoreError, setLoadMoreError] = useState<string | null>(null);

    const tableContainerRef = useRef<HTMLDivElement | null>(null);
    const loadedOffsetsRef = useRef<Set<number>>(new Set());
    const pendingScrollAdjustRef = useRef<{ scrollTop: number; scrollHeight: number } | null>(null);
    const scrollTickingRef = useRef(false);

    const fetchTables = useCallback(async () => {
        setIsLoadingTables(true);
        setTablesError(null);
        try {
            const response = await fetch('/api/database/tables');
            if (!response.ok) throw new Error('Failed to fetch tables');
            const data = (await response.json()) as TableInfo[];
            setTables(data);
        } catch (err) {
            setTablesError(err instanceof Error ? err.message : 'Unknown error');
            setTables([]);
        } finally {
            setIsLoadingTables(false);
        }
    }, []);

    // Fetch available tables on mount (does not load any table data).
    useEffect(() => {
        fetchTables();
    }, [fetchTables]);

    const fetchTableData = useCallback(async (tableName: string, offset = 0) => {
        if (!tableName) return;

        setIsLoadingData(true);
        setDataError(null);
        setLoadMoreError(null);

        try {
            const [dataResponse, statsResponse] = await Promise.all([
                fetch(`/api/database/tables/${tableName}?offset=${offset}`),
                fetch(`/api/database/tables/${tableName}/stats`)
            ]);

            if (!dataResponse.ok || !statsResponse.ok) {
                throw new Error('Failed to fetch table data');
            }

            const [data, stats] = await Promise.all([
                dataResponse.json() as Promise<TableDataPayload>,
                statsResponse.json() as Promise<TableStatsPayload>
            ]);

            dispatch({ type: 'SET_DATABASE_TABLE_DATA', payload: data });
            dispatch({ type: 'SET_DATABASE_TABLE_STATS', payload: stats });
            loadedOffsetsRef.current = new Set([data.offset]);
        } catch (err) {
            setDataError(err instanceof Error ? err.message : 'Unknown error');
            dispatch({ type: 'SET_DATABASE_TABLE_DATA', payload: null });
            dispatch({ type: 'SET_DATABASE_TABLE_STATS', payload: null });
            loadedOffsetsRef.current = new Set();
        } finally {
            setIsLoadingData(false);
        }
    }, [dispatch]);

    const fetchChunk = useCallback(async (tableName: string, offset: number): Promise<TableDataPayload> => {
        const response = await fetch(`/api/database/tables/${tableName}?offset=${offset}`);
        if (!response.ok) {
            throw new Error('Failed to fetch table data');
        }
        return response.json() as Promise<TableDataPayload>;
    }, []);

    const loadNextChunk = useCallback(async () => {
        if (!selectedTable || !tableData || !tableStats) return;
        if (isLoadingData || isLoadingMore) return;

        const nextOffset = tableData.offset + tableData.rows.length;
        if (nextOffset >= tableStats.row_count) return;
        if (loadedOffsetsRef.current.has(nextOffset)) return;

        setIsLoadingMore(true);
        setLoadMoreError(null);
        try {
            const chunk = await fetchChunk(selectedTable, nextOffset);
            loadedOffsetsRef.current.add(chunk.offset);
            dispatch({
                type: 'SET_DATABASE_TABLE_DATA',
                payload: {
                    columns: tableData.columns.length > 0 ? tableData.columns : chunk.columns,
                    rows: [...tableData.rows, ...chunk.rows],
                    offset: tableData.offset,
                    limit: chunk.limit,
                },
            });
        } catch (err) {
            setLoadMoreError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setIsLoadingMore(false);
        }
    }, [dispatch, fetchChunk, isLoadingData, isLoadingMore, selectedTable, tableData, tableStats]);

    const loadPreviousChunk = useCallback(async () => {
        if (!selectedTable || !tableData) return;
        if (isLoadingData || isLoadingMore) return;
        if (tableData.offset <= 0) return;

        const previousOffset = Math.max(0, tableData.offset - tableData.limit);
        if (loadedOffsetsRef.current.has(previousOffset)) return;

        const container = tableContainerRef.current;
        if (container) {
            pendingScrollAdjustRef.current = {
                scrollTop: container.scrollTop,
                scrollHeight: container.scrollHeight,
            };
        }

        setIsLoadingMore(true);
        setLoadMoreError(null);
        try {
            const chunk = await fetchChunk(selectedTable, previousOffset);
            loadedOffsetsRef.current.add(chunk.offset);
            dispatch({
                type: 'SET_DATABASE_TABLE_DATA',
                payload: {
                    columns: tableData.columns.length > 0 ? tableData.columns : chunk.columns,
                    rows: [...chunk.rows, ...tableData.rows],
                    offset: chunk.offset,
                    limit: chunk.limit,
                },
            });
        } catch (err) {
            pendingScrollAdjustRef.current = null;
            setLoadMoreError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setIsLoadingMore(false);
        }
    }, [dispatch, fetchChunk, isLoadingData, isLoadingMore, selectedTable, tableData]);

    useLayoutEffect(() => {
        const pending = pendingScrollAdjustRef.current;
        const container = tableContainerRef.current;
        if (!pending || !container) return;

        const heightDiff = container.scrollHeight - pending.scrollHeight;
        container.scrollTop = pending.scrollTop + heightDiff;
        pendingScrollAdjustRef.current = null;
    }, [tableData?.offset, tableData?.rows.length]);

    const handleTableChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
        const tableName = event.target.value;
        dispatch({ type: 'SET_DATABASE_SELECTED_TABLE', payload: tableName });
        if (tableName) {
            dispatch({ type: 'SET_DATABASE_TABLE_DATA', payload: null });
            dispatch({ type: 'SET_DATABASE_TABLE_STATS', payload: null });
            loadedOffsetsRef.current = new Set();
            fetchTableData(tableName, 0);
        } else {
            dispatch({ type: 'SET_DATABASE_TABLE_DATA', payload: null });
            dispatch({ type: 'SET_DATABASE_TABLE_STATS', payload: null });
            loadedOffsetsRef.current = new Set();
        }
    };

    const handleRefresh = async () => {
        await fetchTables();
        if (selectedTable) {
            loadedOffsetsRef.current = new Set();
            fetchTableData(selectedTable, 0);
        }
    };

    const renderCellValue = (value: unknown): string => {
        if (value === null || value === undefined) return '';
        if (typeof value === 'object') return JSON.stringify(value);
        return String(value);
    };

    const rowCount = tableStats?.row_count ?? 0;
    const hasTable = Boolean(selectedTable);
    const canScroll = Boolean(tableData && tableData.rows.length > 0);
    const canLoadPrev = canScroll && tableData!.offset > 0;
    const canLoadNext = canScroll && tableStats ? (tableData!.offset + tableData!.rows.length) < rowCount : false;

    const handleTableScroll = useCallback(() => {
        const container = tableContainerRef.current;
        if (!container || !canScroll) return;
        if (scrollTickingRef.current) return;

        scrollTickingRef.current = true;
        requestAnimationFrame(() => {
            scrollTickingRef.current = false;
            if (!tableContainerRef.current) return;

            const element = tableContainerRef.current;
            const thresholdPx = 220;
            const distanceFromBottom = element.scrollHeight - (element.scrollTop + element.clientHeight);

            if (element.scrollTop <= thresholdPx && canLoadPrev) {
                void loadPreviousChunk();
            }
            if (distanceFromBottom <= thresholdPx && canLoadNext) {
                void loadNextChunk();
            }
        });
    }, [canLoadNext, canLoadPrev, canScroll, loadNextChunk, loadPreviousChunk]);

    return (
        <div className="database-page">
            <div className="database-header">
                <div className="database-header-label">Data Explorer</div>
                <h1 className="database-title">Database Browser</h1>
                <p className="database-description">
                    Browse historical sessions, prediction logs, and model checkpoints.
                </p>
            </div>

            <div className="database-controls">
                <div className="table-selector-group">
                    <label className="table-selector-label">Select Table</label>
                    <select
                        className="table-selector"
                        value={selectedTable}
                        onChange={handleTableChange}
                        disabled={isLoadingTables || tables.length === 0}
                    >
                        <option value="">-- Select a table --</option>
                        {tables.map((table) => (
                            <option key={table.name} value={table.name}>
                                {table.verbose_name}
                            </option>
                        ))}
                    </select>
                </div>

                <button
                    className={`refresh-button ${(isLoadingTables || isLoadingData) ? 'loading' : ''}`}
                    onClick={handleRefresh}
                    disabled={isLoadingTables || isLoadingData}
                >
                    <RefreshCw />
                    Refresh
                </button>

                {tableStats && (
                    <div className="table-info-bar">
                        <span className="info-bar-table-name">{tableStats.verbose_name}</span>
                        <span className="info-bar-divider">|</span>
                        <span className="info-bar-stat">
                            <strong>{tableStats.column_count}</strong> cols
                        </span>
                        <span className="info-bar-divider">|</span>
                        <span className="info-bar-stat">
                            <strong>{tableStats.row_count}</strong> rows
                        </span>
                    </div>
                )}
            </div>

            {(tablesError || dataError) && (
                <div className="database-empty">
                    <Database />
                    <div className="database-empty-title">Error loading data</div>
                    <div className="database-empty-description">{dataError || tablesError}</div>
                </div>
            )}

            {!tablesError && !dataError && isLoadingData && !tableData && (
                <div className="database-loading">
                    <div className="loading-spinner" />
                </div>
            )}

            {!tablesError && !dataError && !isLoadingData && !tableData && (
                <div className="database-empty">
                    <Table2 />
                    <div className="database-empty-title">No Data Loaded</div>
                    <div className="database-empty-description">
                        {tables.length === 0
                            ? 'Click refresh to load tables, then select a table to view its contents.'
                            : 'Select a table from the dropdown to view its contents.'}
                    </div>
                </div>
            )}

            {!tablesError && !dataError && !isLoadingData && tableData && tableData.rows.length === 0 && (
                <div className="database-empty">
                    <Database />
                    <div className="database-empty-title">Table is Empty</div>
                    <div className="database-empty-description">
                        This table doesn't contain any data yet.
                    </div>
                </div>
            )}

            {!tablesError && !dataError && !isLoadingData && tableData && tableData.rows.length > 0 && (
                <div className="database-table-container" ref={tableContainerRef} onScroll={handleTableScroll}>
                    <table className="database-table">
                        <thead>
                            <tr>
                                {tableData.columns.map((column) => (
                                    <th key={column}>{column}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {tableData.rows.map((row, rowIndex) => (
                                <tr key={rowIndex}>
                                    {tableData.columns.map((column) => (
                                        <td key={column}>{renderCellValue(row[column])}</td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    {hasTable && (isLoadingMore || canLoadNext || canLoadPrev) && (
                        <div className="db-scroll-footer">
                            {isLoadingMore && <div className="db-scroll-loader">Loading…</div>}
                            {!isLoadingMore && loadMoreError && <div className="db-scroll-error">{loadMoreError}</div>}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default DatabasePage;
