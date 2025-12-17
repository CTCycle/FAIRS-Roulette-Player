import React, { useRef, useState } from 'react';
import { Upload, Folder, File, X } from 'lucide-react';

interface FileItem {
    name: string;
    size: number;
    type: string;
}

export const DatasetUpload: React.FC = () => {
    const [files, setFiles] = useState<FileItem[]>([]);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const formatSize = (bytes: number) => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            const newFiles: FileItem[] = Array.from(e.target.files).map(file => ({
                name: file.name,
                size: file.size,
                type: file.type
            }));
            setFiles(prev => [...prev, ...newFiles]);
        }
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.dataTransfer.files) {
            const newFiles: FileItem[] = Array.from(e.dataTransfer.files).map(file => ({
                name: file.name,
                size: file.size,
                type: file.type
            }));
            setFiles(prev => [...prev, ...newFiles]);
        }
    };

    const clearFiles = () => {
        setFiles([]);
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    return (
        <div className="card dataset-section">
            <div className="card-header">
                <h2 className="card-title">
                    <Folder size={24} />
                    Dataset Selection
                </h2>
            </div>

            <div
                className="upload-area"
                onClick={() => fileInputRef.current?.click()}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
            >
                <Upload className="upload-icon" />
                <div className="upload-text">
                    <strong>Click to upload</strong> or drag and drop
                </div>
                <div className="upload-hint">
                    Supports loose images or folders (CSV/XLSX for structured data)
                </div>
                <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    style={{ display: 'none' }}
                    multiple
                    // @ts-expect-error webkitdirectory is non-standard but supported
                    webkitdirectory=""
                />
            </div>

            <button
                type="button"
                className="btn-primary"
                onClick={() => fileInputRef.current?.click()}
            >
                <Upload /> Upload Data
            </button>

            <div className="file-list">
                {files.length > 0 ? (
                    files.map((file, index) => (
                        <div key={index} className="file-item">
                            <File className="file-icon" />
                            <span className="file-name" title={file.name}>{file.name}</span>
                            <span className="file-size">{formatSize(file.size)}</span>
                        </div>
                    ))
                ) : (
                    <div style={{ textAlign: 'center', color: '#9CA3AF', marginTop: '2rem' }}>
                        No files selected
                    </div>
                )}
            </div>

            {files.length > 0 && (
                <button
                    onClick={(e) => { e.stopPropagation(); clearFiles(); }}
                    style={{
                        marginTop: '1rem',
                        background: 'transparent',
                        border: '1px solid #ddd',
                        padding: '0.5rem',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '0.5rem',
                        color: '#666'
                    }}
                >
                    <X size={16} /> Clear Selection
                </button>
            )}
        </div>
    );
};
