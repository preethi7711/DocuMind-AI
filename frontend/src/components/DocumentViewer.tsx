import React from 'react';
import { useUIStore } from '../store/uiStore';
import { FileText } from 'lucide-react';

export const DocumentViewer: React.FC = () => {
  const { selectedDocumentId, activePageNumber } = useUIStore();

  if (!selectedDocumentId) return null;

  // Append #page=N to force the browser's PDF viewer to jump to that page
  const pdfUrl = `http://localhost:8000/api/v1/documents/${selectedDocumentId}/pdf${activePageNumber ? `#page=${activePageNumber}` : ''}`;

  return (
    <div className="flex-1 h-full bg-slate-100 flex flex-col overflow-hidden border-l border-slate-200">
      <div className="h-10 border-b border-slate-200 bg-white flex items-center px-4 shrink-0 shadow-sm">
        <FileText className="w-4 h-4 mr-2 text-slate-500" />
        <span className="text-xs font-semibold text-slate-700 uppercase tracking-wider">Source Document</span>
        {activePageNumber && (
          <span className="ml-3 text-[10px] bg-primary-100 text-primary-700 px-2 py-0.5 rounded-full font-bold">
            Page {activePageNumber}
          </span>
        )}
      </div>
      <div className="flex-1 w-full bg-slate-200">
        <iframe 
          key={pdfUrl} // Key changes force iframe reload so #page hash is respected
          src={pdfUrl} 
          className="w-full h-full border-none"
          title="Document Viewer"
        />
      </div>
    </div>
  );
};
