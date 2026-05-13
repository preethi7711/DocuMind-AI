import { DocumentSidebar } from './components/DocumentSidebar';
import { UploadPanel } from './components/UploadPanel';
import { ChatInterface } from './components/ChatInterface';
import { DocumentViewer } from './components/DocumentViewer';
import { DeveloperToolsPanel } from './components/DeveloperToolsPanel';
import { useUIStore } from './store/uiStore';
import { Layout, BrainCircuit, Bug } from 'lucide-react';

function App() {
  const { selectedDocumentId, documents, addDocument, isDebugMode, toggleDebugMode } = useUIStore();

  return (
    <div className="flex h-screen w-full bg-slate-50 overflow-hidden text-slate-900 font-sans">
      {/* Sidebar */}
      <DocumentSidebar />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col h-full relative">
        {/* Header */}
        <header className="h-14 border-b border-slate-200 bg-white flex items-center justify-between px-6 shrink-0">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-primary-600 flex items-center justify-center shadow-sm">
              <BrainCircuit className="w-5 h-5 text-white" />
            </div>
            <h1 className="font-bold text-lg text-slate-800 tracking-tight">DocuMind <span className="text-primary-600 font-black">AI</span></h1>
          </div>
          
          {selectedDocumentId && (
            <div className="flex items-center space-x-3">
              <div className="flex items-center text-sm font-medium text-slate-600 bg-slate-100 px-3 py-1.5 rounded-full border border-slate-200">
                <Layout className="w-4 h-4 mr-2 text-primary-500" />
                {documents.find(d => d.id === selectedDocumentId)?.filename || 'Unknown Document'}
              </div>
              <button 
                onClick={toggleDebugMode}
                className={`p-1.5 rounded-md transition-colors ${isDebugMode ? 'bg-primary-100 text-primary-700' : 'text-slate-400 hover:bg-slate-100 hover:text-slate-600'}`}
                title="Toggle Retrieval Inspector"
              >
                <Bug className="w-5 h-5" />
              </button>
            </div>
          )}
        </header>

        {/* Content Body */}
        <div className="flex-1 overflow-hidden">
          {selectedDocumentId ? (
            <div className="flex h-full">
              {/* Chat Interface takes up left area */}
              <div className="flex-1 min-w-[500px] border-r border-slate-200">
                <ChatInterface />
              </div>
              
              {/* Document Viewer takes up right area */}
              <div className="w-1/2 hidden lg:flex flex-col">
                <DocumentViewer />
              </div>

              {/* Developer Tools Panel */}
              <DeveloperToolsPanel />
            </div>
          ) : (
            <div className="h-full flex items-center justify-center p-6 overflow-y-auto">
              <UploadPanel onUploadSuccess={addDocument} />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
