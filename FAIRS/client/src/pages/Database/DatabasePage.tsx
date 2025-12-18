import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Database, Table2 } from 'lucide-react';
import { useAppState } from '../../context/AppStateContext';
import './Database.css';

interface TableInfo {
    name: string;
    verbose_name: string;
}

const DatabasePage: React.FC = () => {
    const { state, dispatch } = useAppState();
    const { selectedTable, tableData, tableStats } = state.database;

    const [tables, setTables] = useState<TableInfo[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Fetch available tables on mount
    useEffect(() => {
        const fetchTables = async () => {
            try {
                const response = await fetch('/api/database/tables');
                if (!response.ok) throw new Error('Failed to fetch tables');
                const data = await response.json();
                setTables(data);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Unknown error');
            }
        };
        fetchTables();
    }, []);

    const fetchTableData = useCallback(async (tableName: string) => {
        if (!tableName) return;

        setIsLoading(true);
        setError(null);

        try {
            const [dataResponse, statsResponse] = await Promise.all([
                fetch(`/api/database/tables/${tableName}`),
                fetch(`/api/database/tables/${tableName}/stats`)
            ]);

            if (!dataResponse.ok || !statsResponse.ok) {
                throw new Error('Failed to fetch table data');
            }

            const [data, stats] = await Promise.all([
                dataResponse.json(),
                statsResponse.json()
            ]);

            dispatch({ type: 'SET_DATABASE_TABLE_DATA', payload: data });
            dispatch({ type: 'SET_DATABASE_TABLE_STATS', payload: stats });
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
            dispatch({ type: 'SET_DATABASE_TABLE_DATA', payload: null });
            dispatch({ type: 'SET_DATABASE_TABLE_STATS', payload: null });
        } finally {
            setIsLoading(false);
        }
    }, [dispatch]);

    const handleTableChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
        const tableName = event.target.value;
        dispatch({ type: 'SET_DATABASE_SELECTED_TABLE', payload: tableName });
        if (tableName) {
            fetchTableData(tableName);
        } else {
            dispatch({ type: 'SET_DATABASE_TABLE_DATA', payload: null });
            dispatch({ type: 'SET_DATABASE_TABLE_STATS', payload: null });
        }
    };

    const handleRefresh = () => {
        if (selectedTable) {
            fetchTableData(selectedTable);
        }
    };

    const renderCellValue = (value: unknown): string => {
        if (value === null || value === undefined) return '';
        if (typeof value === 'object') return JSON.stringify(value);
        return String(value);
    };

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
                    className={`refresh-button ${isLoading ? 'loading' : ''}`}
                    onClick={handleRefresh}
                    disabled={!selectedTable || isLoading}
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

            {error && (
                <div className="database-empty">
                    <Database />
                    <div className="database-empty-title">Error loading data</div>
                    <div className="database-empty-description">{error}</div>
                </div>
            )}

            {!error && isLoading && (
                <div className="database-loading">
                    <div className="loading-spinner" />
                </div>
            )}

            {!error && !isLoading && !tableData && (
                <div className="database-empty">
                    <Table2 />
                    <div className="database-empty-title">No Data Loaded</div>
                    <div className="database-empty-description">
                        Select a table from the dropdown to view its contents.
                    </div>
                </div>
            )}

            {!error && !isLoading && tableData && tableData.rows.length === 0 && (
                <div className="database-empty">
                    <Database />
                    <div className="database-empty-title">Table is Empty</div>
                    <div className="database-empty-description">
                        This table doesn't contain any data yet.
                    </div>
                </div>
            )}

            {!error && !isLoading && tableData && tableData.rows.length > 0 && (
                <div className="database-table-container">
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
                </div>
            )}
        </div>
    );
};

export default DatabasePage;
