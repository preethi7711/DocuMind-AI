import React from 'react';
import { FileText, Plus, ChevronLeft, ChevronRight, CheckCircle2 } from 'lucide-react';
import { useUIStore } from '../store/uiStore';

export const DocumentSidebar: React.FC = () => {
  const { 
    documents, 
    selectedDocumentId, 
    setSelectedDocument, 
    isSidebarOpen, 
    toggleSidebar 
  } = useUIStore();

  if (!isSidebarOpen) {
    return (
      <div className="h-full border-r border-slate-200 bg-white p-2 flex flex-col items-center">
        <button 
          onClick={toggleSidebar}
          className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
    );
  }

  return (
    <div className="w-64 h-full border-r border-slate-200 bg-slate-50 flex flex-col transition-all">
      <div className="p-4 border-b border-slate-200 flex justify-between items-center">
        <h2 className="font-semibold text-slate-800 flex items-center">
          <FileText className="w-4 h-4 mr-2" />
          Workspace
        </h2>
        <button 
          onClick={toggleSidebar}
          className="p-1 text-slate-500 hover:text-slate-800 hover:bg-slate-200 rounded-md"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
      </div>

      <div className="p-4">
        <button 
          onClick={() => setSelectedDocument(null)}
          className="w-full flex items-center justify-center px-4 py-2 bg-white border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 hover:border-slate-400 transition-all shadow-sm"
        >
          <Plus className="w-4 h-4 mr-2" />
          New Document
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2">
        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-2 mb-2">
          Your Documents
        </div>
        
        {documents.length === 0 ? (
          <div className="px-2 py-4 text-sm text-slate-500 italic">
            No documents uploaded yet.
          </div>
        ) : (
          <ul className="space-y-1">
            {documents.map((doc) => (
              <li key={doc.id}>
                <button
                  onClick={() => setSelectedDocument(doc.id)}
                  className={`w-full text-left px-3 py-2.5 rounded-lg text-sm flex flex-col transition-colors ${
                    selectedDocumentId === doc.id
                      ? 'bg-primary-50 border border-primary-200'
                      : 'hover:bg-slate-200/50 border border-transparent'
                  }`}
                >
                  <span className={`font-medium truncate block ${
                    selectedDocumentId === doc.id ? 'text-primary-700' : 'text-slate-700'
                  }`}>
                    {doc.filename}
                  </span>
                  
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-xs text-slate-500 truncate">
                      {new Date(doc.upload_time).toLocaleDateString()}
                    </span>
                    {doc.status === 'completed' && (
                      <CheckCircle2 className="w-3 h-3 text-green-500" />
                    )}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};
