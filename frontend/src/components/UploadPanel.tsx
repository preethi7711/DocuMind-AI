import React, { useState } from 'react';
import { Upload, FileType, CheckCircle, Loader2 } from 'lucide-react';
import { documentService } from '../services/api';
import type { DocumentResponse } from '../types/api';

interface UploadPanelProps {
  onUploadSuccess: (doc: DocumentResponse) => void;
}

export const UploadPanel: React.FC<UploadPanelProps> = ({ onUploadSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type === 'application/pdf') {
        setFile(droppedFile);
        setError(null);
      } else {
        setError('Please upload a valid PDF document.');
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFile = e.target.files[0];
      if (selectedFile.type === 'application/pdf') {
        setFile(selectedFile);
        setError(null);
      } else {
        setError('Please upload a valid PDF document.');
      }
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    
    setIsUploading(true);
    setError(null);
    
    try {
      const response = await documentService.uploadDocument(file);
      if (response.success) {
        onUploadSuccess(response.data);
        setFile(null);
      } else {
        setError(response.message || 'Upload failed');
      }
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'An error occurred during upload.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-6 bg-white rounded-xl shadow-sm border border-slate-200">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-slate-800">Upload Document</h2>
        <p className="text-sm text-slate-500 mt-1">Upload a PDF to extract structured intelligence.</p>
      </div>

      <div 
        className={`relative flex flex-col items-center justify-center p-12 border-2 border-dashed rounded-lg transition-colors ${
          isDragging ? 'border-primary-500 bg-primary-50' : 'border-slate-300 hover:border-slate-400 bg-slate-50'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input 
          type="file" 
          accept=".pdf" 
          onChange={handleFileChange} 
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          disabled={isUploading}
        />
        
        {file ? (
          <div className="flex flex-col items-center text-center">
            <FileType className="w-12 h-12 text-primary-500 mb-3" />
            <p className="font-medium text-slate-700">{file.name}</p>
            <p className="text-xs text-slate-500 mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
          </div>
        ) : (
          <div className="flex flex-col items-center text-center">
            <div className="w-16 h-16 rounded-full bg-primary-100 flex items-center justify-center mb-4">
              <Upload className="w-8 h-8 text-primary-600" />
            </div>
            <p className="font-medium text-slate-700 text-lg">Click or drag PDF to upload</p>
            <p className="text-sm text-slate-500 mt-2">Maximum file size 50MB</p>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-4 p-3 bg-red-50 text-red-700 text-sm rounded-lg border border-red-200">
          {error}
        </div>
      )}

      <div className="mt-6 flex justify-end">
        <button
          onClick={handleUpload}
          disabled={!file || isUploading}
          className={`flex items-center justify-center px-6 py-2.5 rounded-lg font-medium text-white transition-all ${
            !file || isUploading ? 'bg-slate-300 cursor-not-allowed' : 'bg-primary-600 hover:bg-primary-700 shadow-sm'
          }`}
        >
          {isUploading ? (
            <>
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              Uploading...
            </>
          ) : (
            <>
              <CheckCircle className="w-5 h-5 mr-2" />
              Process Document
            </>
          )}
        </button>
      </div>
    </div>
  );
};
