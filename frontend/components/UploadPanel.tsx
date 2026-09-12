'use client';
import { useRef, useState } from 'react';
import { ArrowUpRight, FileSpreadsheet, Loader2, UploadCloud } from 'lucide-react';
import { api } from '../lib/api';

export default function UploadPanel({ onDone }: { onDone?: (id:number)=>void }) {
  const ref = useRef<HTMLInputElement>(null); const [file,setFile]=useState<File|null>(null); const [company,setCompany]=useState(''); const [companies,setCompanies]=useState<string[]>([]); const [busy,setBusy]=useState(false); const [error,setError]=useState('');
  async function chooseFile(next: File | null) {
    setFile(next); setCompany(''); setCompanies([]); setError('');
    if (!next || !next.name.toLowerCase().endsWith('.csv')) return;
    try {
      const text = await next.text();
      const lines = text.split(/\r?\n/).filter(Boolean);
      if (lines.length < 2) return;
      const headers = lines[0].split(',').map(value => value.trim().replace(/^"|"$/g, ''));
      const companyIndex = headers.findIndex(value => /company|entity|business|organization|customer|client/i.test(value));
      if (companyIndex < 0) return;
      const values = Array.from(new Set(lines.slice(1).map(line => line.split(',')[companyIndex]?.trim().replace(/^"|"$/g, '')).filter(Boolean)));
      setCompanies(values.slice(0, 200));
    } catch { /* Excel files can still use the manual company field. */ }
  }
  async function submit() { if(!file) return; setBusy(true); setError(''); try { const r=await api.upload(file, company || undefined); onDone?.(r.review_id); } catch(e:any){ setError(e.message || 'Upload failed'); } finally { setBusy(false); } }
  return <section className="ingest-card">
    <div className="ingest-glow"/><div className="ingest-copy"><div className="eyebrow"><UploadCloud size={14}/> DATASET INGESTION</div><h2>Drop the evidence.<br/><span>We map the universe.</span></h2><p>CSV, XLS or XLSX. FINORA preserves the original rows, discovers sheets, profiles every column and builds an explainable data map.</p><div className="drop-actions"><button className="primary" onClick={()=>ref.current?.click()}><FileSpreadsheet size={17}/> {file ? file.name : 'Choose dataset'} <ArrowUpRight size={16}/></button>{file && <button className="ghost" onClick={submit} disabled={busy}>{busy?<Loader2 className="spin" size={16}/>:<SparkIcon/>}{busy?'Profiling…':'Analyze dataset'}</button>}</div>{file && <label className="company-scope">INCLUDE COMPANY<select value={company} onChange={event=>setCompany(event.target.value)}><option value="">All companies</option>{companies.map(name=><option key={name} value={name}>{name}</option>)}</select>{!companies.length && <input value={company} onChange={event=>setCompany(event.target.value)} placeholder="Optional company name" />}</label>}{error&&<div className="error">{error}</div>}<input ref={ref} hidden type="file" accept=".csv,.xlsx,.xls" onChange={e=>chooseFile(e.target.files?.[0]||null)}/></div>
    <div className="ingest-visual"><div className="scan-ring r1"/><div className="scan-ring r2"/><div className="scan-ring r3"/><div className="data-core"><DatabaseIcon/><span>INGEST</span></div><div className="node n1">CSV</div><div className="node n2">XLSX</div><div className="node n3">RAW</div><div className="node n4">AI</div></div>
  </section>
}
function SparkIcon(){return <span style={{fontSize:16}}>✦</span>}; function DatabaseIcon(){return <span className="db-icon">◈</span>}
