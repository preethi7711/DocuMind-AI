import requests
import time
import os

BASE_URL = "http://127.0.0.1:8000/api/v1"
PDF_PATH = "test_documind_v2.pdf"

def test_pipeline():
    print(f"--- Starting E2E Test ---")
    
    # 1. Upload
    print(f"1. Uploading {PDF_PATH}...")
    with open(PDF_PATH, 'rb') as f:
        files = {'file': (PDF_PATH, f, 'application/pdf')}
        response = requests.post(f"{BASE_URL}/documents/upload", files=files)
    
    if response.status_code != 200:
        print(f"Upload failed: {response.text}")
        return
    
    data = response.json()['data']
    doc_id = data['id']
    print(f"   Success! Document ID: {doc_id}")
    
    # 2. Poll Status
    print(f"2. Waiting for processing to complete...")
    max_retries = 30
    for i in range(max_retries):
        resp = requests.get(f"{BASE_URL}/documents/{doc_id}")
        status = resp.json()['data']['status']
        print(f"   [{i+1}/{max_retries}] Current status: {status}")
        
        if status == 'completed':
            print("   Success! Processing finished.")
            break
        elif status == 'error':
            print("   Error! Processing failed.")
            return
        
        time.sleep(5)
    else:
        print("   Timeout waiting for processing.")
        return
    
    # 3. Chat
    print(f"3. Asking a question...")
    chat_payload = {
        "document_id": doc_id,
        "messages": [
            {"role": "user", "content": "What is this document about? Summarize it in 2 sentences."}
        ],
        "debug": True
    }
    
    start_time = time.time()
    resp = requests.post(f"{BASE_URL}/chat", json=chat_payload)
    end_time = time.time()
    
    if resp.status_code != 200:
        print(f"Chat failed: {resp.text}")
        return
    
    data = resp.json()['data']
    answer = data['answer']
    print(f"\n--- AI ANSWER ({end_time - start_time:.2f}s) ---")
    print(answer)
    print(f"--------------------------")
    
    if 'citations' in data:
        print(f"Citations: {len(data['citations'])} found.")
        
    if 'trace' in data and data['trace']:
        print(f"\n--- RETRIEVAL TRACE ---")
        trace = data['trace']
        print(f"Original Query: {trace.get('original_query')}")
        results = trace.get('reranking_results', [])
        print(f"Scored {len(results)} chunks.")
        for i, res in enumerate(results):
            print(f"\nChunk {i+1} [{res.get('status').upper()}]:")
            print(f"  ID: {res.get('chunk_id')}")
            print(f"  Final Score: {res.get('final_score')}")
            print(f"  Semantic Sim: {res.get('semantic_similarity')}")
            print(f"  OCR Conf: {res.get('ocr_confidence')}")
            print(f"  Heading: {res.get('heading')}")
            print(f"  Snippet: {res.get('text_snippet')}")

if __name__ == "__main__":
    test_pipeline()
