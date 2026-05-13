import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, ChevronDown, ChevronUp, BookOpen } from 'lucide-react';
import { useUIStore } from '../store/uiStore';
import { chatService } from '../services/api';

export const ChatInterface: React.FC = () => {
  const { selectedDocumentId, chatHistory, addChatMessage, updateLastChatMessage, isDebugMode } = useUIStore();
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [streamingStatus, setStreamingStatus] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const messages = selectedDocumentId ? chatHistory[selectedDocumentId] || [] : [];

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingStatus]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || !selectedDocumentId || isLoading) return;

    const userMsg = inputValue.trim();
    setInputValue('');
    
    // Add user message to UI immediately
    addChatMessage(selectedDocumentId, { role: 'user', content: userMsg });
    
    // Add empty assistant message to stream into
    addChatMessage(selectedDocumentId, { role: 'assistant', content: '' });
    
    setIsLoading(true);
    setStreamingStatus('Analyzing query intent...');

    try {
      const historyToSend = [...messages, { role: 'user' as const, content: userMsg }];
      
      let currentText = '';
      
      await chatService.askQuestionStream(
        selectedDocumentId, 
        historyToSend, 
        isDebugMode,
        // onChunk callback
        (chunk) => {
          setStreamingStatus(''); // Clear status once we start getting tokens
          currentText += chunk;
          updateLastChatMessage(selectedDocumentId, { content: currentText });
        },
        // onMetadata callback
        (citations, trace) => {
          updateLastChatMessage(selectedDocumentId, { citations, trace });
        }
      );
      
    } catch (error) {
      console.error("Chat error:", error);
      updateLastChatMessage(selectedDocumentId, { 
        content: "I encountered an error connecting to the server. Please try again." 
      });
    } finally {
      setIsLoading(false);
      setStreamingStatus('');
    }
  };

  if (!selectedDocumentId) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-slate-50 text-slate-400">
        <Bot className="w-16 h-16 mb-4 opacity-20" />
        <p>Select a document to start chatting</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-white relative">
      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto">
            <div className="w-12 h-12 rounded-full bg-primary-100 text-primary-600 flex items-center justify-center mb-4">
              <Bot className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-semibold text-slate-800">DocuMind AI</h3>
            <p className="text-slate-500 mt-2 text-sm">
              I have analyzed this document. Ask me anything about its contents, 
              themes, or specific details.
            </p>
          </div>
        ) : (
          messages.map((msg, index) => (
            <div 
              key={index} 
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`flex max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                  msg.role === 'user' ? 'bg-slate-800 text-white ml-3' : 'bg-primary-600 text-white mr-3'
                }`}>
                  {msg.role === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
                </div>
                
                <div className={`px-4 py-3 rounded-2xl ${
                  msg.role === 'user' 
                    ? 'bg-slate-800 text-white rounded-tr-sm' 
                    : 'bg-slate-100 text-slate-800 rounded-tl-sm border border-slate-200 shadow-sm'
                }`}>
                  <p className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</p>
                  
                  {/* Inline Citations Accordion */}
                  {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                    <CitationAccordion citations={msg.citations} />
                  )}
                </div>
              </div>
            </div>
          ))
        )}
        
        {isLoading && streamingStatus && (
          <div className="flex justify-start">
            <div className="flex max-w-[80%] flex-row">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary-600 text-white mr-3 flex items-center justify-center">
                <Loader2 className="w-4 h-4 animate-spin" />
              </div>
              <div className="px-5 py-3 rounded-2xl bg-slate-100 rounded-tl-sm flex items-center">
                <span className="text-xs font-medium text-slate-500 italic animate-pulse">
                  {streamingStatus}
                </span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-white border-t border-slate-200">
        <form 
          onSubmit={handleSubmit}
          className="max-w-3xl mx-auto relative flex items-end border border-slate-300 rounded-xl bg-white shadow-sm focus-within:ring-2 focus-within:ring-primary-500/20 focus-within:border-primary-500 transition-all overflow-hidden"
        >
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            placeholder="Ask a question about this document..."
            className="w-full max-h-32 min-h-[56px] py-4 pl-4 pr-12 bg-transparent resize-none outline-none text-slate-800 text-sm"
            rows={1}
          />
          <button
            type="submit"
            disabled={!inputValue.trim() || isLoading}
            className={`absolute right-2 bottom-2 p-2 rounded-lg transition-colors ${
              !inputValue.trim() || isLoading 
                ? 'text-slate-400 bg-transparent cursor-not-allowed' 
                : 'text-white bg-primary-600 hover:bg-primary-700 shadow-sm'
            }`}
          >
            {isLoading ? <Loader2 className="w-5 h-5 animate-spin text-primary-600" /> : <Send className="w-4 h-4" />}
          </button>
        </form>
        <p className="text-center text-xs text-slate-400 mt-3">
          DocuMind AI can make mistakes. Consider verifying important information.
        </p>
      </div>
    </div>
  );
};

// Sub-component for Citations
const CitationAccordion: React.FC<{ citations: any[] }> = ({ citations }) => {
  const [isOpen, setIsOpen] = useState(false);
  const { setActivePageNumber } = useUIStore();

  if (!citations || citations.length === 0) return null;

  return (
    <div className="mt-4 border-t border-slate-200 pt-3">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center text-xs font-medium text-slate-500 hover:text-slate-700 transition-colors"
      >
        <BookOpen className="w-3.5 h-3.5 mr-1.5" />
        {citations.length} Reference{citations.length !== 1 ? 's' : ''}
        {isOpen ? <ChevronUp className="w-3.5 h-3.5 ml-1" /> : <ChevronDown className="w-3.5 h-3.5 ml-1" />}
      </button>

      {isOpen && (
        <div className="mt-3 space-y-2">
          {citations.map((cite, idx) => (
            <button 
              key={idx} 
              onClick={() => cite.page_number && setActivePageNumber(cite.page_number)}
              className="w-full text-left bg-white p-3 rounded-lg border border-slate-200 shadow-sm hover:border-primary-300 hover:shadow-md transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center overflow-hidden">
                  <span className="inline-flex items-center justify-center w-4 h-4 shrink-0 rounded-full bg-primary-100 text-primary-700 text-[10px] font-bold mr-2 group-hover:bg-primary-600 group-hover:text-white transition-colors">
                    {idx + 1}
                  </span>
                  <span className="text-xs font-semibold text-slate-700 truncate group-hover:text-primary-700 transition-colors">
                    {cite.heading}
                  </span>
                </div>
                {cite.page_number && (
                  <span className="text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded ml-2 shrink-0 group-hover:bg-primary-50 group-hover:text-primary-600">
                    Pg {cite.page_number}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-600 line-clamp-3 pl-6 border-l-2 border-slate-100 italic group-hover:border-primary-200 transition-colors">
                "{cite.text_snippet}"
              </p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
