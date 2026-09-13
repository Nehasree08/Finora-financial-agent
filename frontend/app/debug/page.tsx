'use client';
import { useState } from 'react';

export default function DebugPage() {
  const [status, setStatus] = useState('');

  async function testGet() {
    try {
      setStatus('Testing GET...');
      const res = await fetch('http://127.0.0.1:8000/health');
      setStatus(`GET /health: ${res.status}`);
    } catch (e: any) {
      setStatus(`GET Error: ${e.message}`);
    }
  }

  async function testPost() {
    try {
      setStatus('Testing POST...');
      const res = await fetch('http://127.0.0.1:8000/reviews', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ test: 'data' }),
      });
      setStatus(`POST /reviews: ${res.status}`);
    } catch (e: any) {
      setStatus(`POST Error: ${e.message}`);
    }
  }

  async function testFileUpload() {
    try {
      setStatus('Testing File Upload...');
      const blob = new Blob(['Company,Revenue\nApple,100'], { type: 'text/csv' });
      const form = new FormData();
      form.append('file', blob, 'test.csv');
      
      const res = await fetch('http://127.0.0.1:8000/reviews', {
        method: 'POST',
        body: form,
      });
      const data = await res.json();
      setStatus(`File Upload: ${res.status} - ${JSON.stringify(data)}`);
    } catch (e: any) {
      setStatus(`Upload Error: ${e.message}`);
    }
  }

  return (
    <div style={{ padding: '20px' }}>
      <h1>Debug API Tests</h1>
      <button onClick={testGet} style={{ margin: '5px' }}>Test GET</button>
      <button onClick={testPost} style={{ margin: '5px' }}>Test POST</button>
      <button onClick={testFileUpload} style={{ margin: '5px' }}>Test File Upload</button>
      <pre style={{ marginTop: '20px', padding: '10px', background: '#f0f0f0' }}>{status}</pre>
    </div>
  );
}
