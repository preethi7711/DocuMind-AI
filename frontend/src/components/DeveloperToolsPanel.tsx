import React from 'react';
import { useUIStore } from '../store/uiStore';
import { Bug, X, ChevronRight, AlertTriangle, CheckCircle2 } from 'lucide-react';

export const DeveloperToolsPanel: React.FC = () => {
  const { isDebugMode, toggleDebugMode, selectedDocumentId, chatHistory } = useUIStore();
  
  if (!isDebugMode) return null;

  const messages = selectedDocumentId ? chatHistory[selectedDocumentId] || [] : [];
  
  // Find the latest assistant message with a trace
  const latestTraceMsg = [...messages].reverse().find(m => m.role === 'assistant' && m.trace);
  const trace = latestTraceMsg?.trace;

  return (
    <div className="w-96 h-full bg-slate-900 text-slate-300 border-l border-slate-700 flex flex-col shrink-0 overflow-hidden font-mono text-sm shadow-xl z-20">
      {/* Header */}
      <div className="h-14 border-b border-slate-700 bg-slate-900 flex items-center justify-between px-4 shrink-0 text-white">
        <div className="flex items-center">
          <Bug className="w-4 h-4 mr-2 text-primary-400" />
          <span className="font-semibold tracking-wider text-xs">RETRIEVAL INSPECTOR</span>
        </div>
        <button onClick={toggleDebugMode} className="text-slate-400 hover:text-white transition-colors">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {!trace ? (
          <div className="text-center text-slate-500 mt-10">
            <Bug className="w-8 h-8 mx-auto mb-2 opacity-20" />
            <p>Send a message to see the retrieval trace.</p>
          </div>
        ) : (
          <>
            {/* Query Info */}
            <div className="bg-slate-800 rounded-lg p-3 border border-slate-700">
              <h3 className="text-xs font-bold text-slate-400 mb-2 uppercase tracking-widest">Query Analyzer</h3>
              <p className="text-primary-300">"{trace.original_query}"</p>
            </div>

            {/* Chunks */}
            <div>
              <h3 className="text-xs font-bold text-slate-400 mb-3 uppercase tracking-widest flex items-center">
                <ChevronRight className="w-4 h-4 mr-1" /> Reranked Chunks ({trace.reranking_results?.length || 0})
              </h3>
              
              <div className="space-y-4">
                {trace.reranking_results?.map((chunk: any, i: number) => {
                  const conf = chunk.ocr_confidence || 0;
                  const isLowConf = conf < 0.7;
                  const isHighConf = conf >= 0.9;
                  const sim = chunk.semantic_similarity || 0;
                  const isWeakMatch = sim < 0.6; 
                  
                  const isDiscarded = chunk.status === 'discarded';
                  const isPenalized = chunk.status === 'penalized';

                  return (
                    <div key={i} className={`bg-slate-800 rounded-lg p-3 border relative overflow-hidden ${isDiscarded ? 'border-red-900/50 opacity-50' : isPenalized ? 'border-yellow-900' : 'border-slate-700'}`}>
                      {/* Status Indicator Line */}
                      <div className={`absolute left-0 top-0 bottom-0 w-1 ${isDiscarded ? 'bg-red-500' : isPenalized ? 'bg-yellow-500' : 'bg-emerald-500'}`} />
                      
                      <div className="pl-2">
                        <div className="flex items-start justify-between mb-2">
                          <span className={`font-bold text-xs truncate mr-2 ${isDiscarded ? 'text-red-400 line-through' : 'text-white'}`} title={chunk.heading}>
                            {chunk.heading}
                          </span>
                          <span className="flex space-x-1 shrink-0">
                            {isDiscarded && <span className="text-[9px] uppercase tracking-wider bg-red-900/50 text-red-400 px-1.5 py-0.5 rounded">Discarded</span>}
                            {isPenalized && <span className="text-[9px] uppercase tracking-wider bg-yellow-900/50 text-yellow-400 px-1.5 py-0.5 rounded">Penalized</span>}
                            <span className="text-[10px] bg-slate-700 px-1.5 py-0.5 rounded text-slate-300">
                              #{i + 1}
                            </span>
                          </span>
                        </div>

                        <div className="flex flex-wrap gap-2 mb-3">
                          {/* Final Score */}
                          <div className={`flex items-center text-[10px] px-2 py-1 rounded bg-slate-900 border border-slate-700 text-white`}>
                            <span className="mr-1">Score:</span>
                            <span className="font-bold text-primary-400">{chunk.final_score.toFixed(3)}</span>
                          </div>

                          {/* Semantic Similarity */}
                          <div className={`flex items-center text-[10px] px-2 py-1 rounded bg-slate-900 border ${isWeakMatch ? 'border-red-900 text-red-400' : 'border-slate-700 text-slate-300'}`}>
                            <span className="mr-1">Sim:</span>
                            <span className="font-bold">{sim.toFixed(3)}</span>
                          </div>

                          {/* Confidence Score */}
                          <div className={`flex items-center text-[10px] px-2 py-1 rounded bg-slate-900 border ${isLowConf ? 'border-red-900 text-red-400' : isHighConf ? 'border-emerald-900 text-emerald-400' : 'border-yellow-900 text-yellow-400'}`}>
                            <span className="mr-1">OCR:</span>
                            <span className="font-bold">{(conf * 100).toFixed(0)}%</span>
                            {isLowConf ? <AlertTriangle className="w-3 h-3 ml-1" /> : <CheckCircle2 className="w-3 h-3 ml-1" />}
                          </div>
                        </div>

                        <div className="text-xs text-slate-400 line-clamp-3 italic border-l-2 border-slate-600 pl-2">
                          {chunk.text_snippet}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
