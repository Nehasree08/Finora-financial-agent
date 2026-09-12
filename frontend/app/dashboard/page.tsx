'use client';
import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, BrainCircuit, Database, FileCheck2, Fingerprint, Gauge, Layers3, Radar, ShieldCheck, Sparkles } from 'lucide-react';
import Link from 'next/link';
import AppShell from '../../components/AppShell';
import UploadPanel from '../../components/UploadPanel';
import MetricCard from '../../components/MetricCard';
import SignalMap from '../../components/SignalMap';
import { api, Review } from '../../lib/api';
import { bytes, date, integer } from '../../lib/format';

export default function Dashboard(){
 const [reviews,setReviews]=useState<Review[]>([]); const [loading,setLoading]=useState(true);
 useEffect(()=>{api.reviews().then(r=>setReviews(r.items||[])).catch(()=>{}).finally(()=>setLoading(false));},[]);
 const latest=reviews[0]; const ds=latest?.datasets||[]; const rows=ds.reduce((a,d)=>a+d.row_count,0), cols=ds.reduce((a,d)=>a+d.column_count,0), missing=ds.reduce((a,d)=>a+d.missing_count,0), dup=ds.reduce((a,d)=>a+d.duplicate_count,0);
 const ai = useMemo(()=>latest ? [`${ds.length} table${ds.length===1?'':'s'} discovered from the source file.`,`Schema fingerprint ${latest.uploaded_file?.sha256?.slice(0,12)||'pending'}…`, missing ? `${missing} missing values detected — validation should inspect these fields.` : 'No missing values detected in the profiled tables.', dup ? `${dup} duplicate row${dup===1?'':'s'} detected.` : 'No duplicate rows detected in the profiled tables.'] : ['No dataset has entered the audit core yet. Upload evidence to activate intelligence.'],[latest,ds.length,missing,dup]);
 return <AppShell><div className="page">
   <section className="hero-grid"><div className="hero-copy"><div className="eyebrow"><Sparkles size={14}/> THE AUDIT OPERATING SYSTEM</div><h2>See the <i>whole</i> financial story.</h2><p>FINORA turns an unknown spreadsheet into a navigable evidence universe — preserving source data while revealing structure, risk signals and explainable next actions.</p><div className="hero-tags"><span><Fingerprint size={13}/> Source-preserving</span><span><ShieldCheck size={13}/> Deterministic core</span><span><BrainCircuit size={13}/> AI-assisted</span></div></div><div className="hero-orbit"><div className="orbit o1"/><div className="orbit o2"/><div className="orbit o3"/><div className="hero-center"><Gauge size={23}/><b>{latest?'READY':'WAITING'}</b><small>audit state</small></div><span className="orbit-label ol1">DISCOVER</span><span className="orbit-label ol2">PROFILE</span><span className="orbit-label ol3">EXPLAIN</span></div></section>
  <UploadPanel onDone={(id)=>window.location.href=`/reviews/${id}`}/>
   <section className="section-head"><div><span className="eyebrow">AUDIT TELEMETRY</span><h3>What the engine knows</h3></div><span className="muted">{loading?'syncing…':latest?`latest review · ${date(latest.created_at)}`:'No reviews yet'}</span></section>
   <div className="metric-grid"><MetricCard label="Records" value={integer(rows)} sub={latest?`${ds.length} source tables` : undefined} icon={Database}/><MetricCard label="Fields" value={integer(cols)} sub={latest?'schema mapped':'Upload to map'} icon={Layers3}/><MetricCard label="Missing values" value={integer(missing)} sub={latest?(missing?'validation required':'clean profile') : undefined} icon={FileCheck2} tone={missing?'warn':''}/><MetricCard label="Duplicate rows" value={integer(dup)} sub={latest?(dup?'investigate':'none detected'):undefined} icon={Radar} tone={dup?'warn':''}/></div>
  <div className="lower-grid"><SignalMap columns={cols} rows={rows} missing={missing} duplicates={dup}/><section className="ai-card"><div className="ai-header"><div className="ai-icon"><BrainCircuit size={18}/></div><div><span>AI EVIDENCE COPILOT</span><small>grounded in persisted profile metadata</small></div><b>β</b></div><div className="ai-body">{ai.map((x,i)=><div className="signal" key={i}><span>{String(i+1).padStart(2,'0')}</span><p>{x}</p></div>)}</div>{latest&&<Link className="ai-cta" href={`/reviews/${latest.id}`}>Open evidence room <ArrowRight size={16}/></Link>}</section></div>
  <section className="recent"><div className="section-head"><div><span className="eyebrow">SOURCE VAULT</span><h3>Recent reviews</h3></div><Link href="/reviews" className="text-link">View vault <ArrowRight size={15}/></Link></div>{reviews.length===0?<div className="empty"><Database size={24}/><b>Nothing ingested yet</b><span>Upload your first financial dataset above.</span></div>:<div className="review-list">{reviews.slice(0,5).map(r=><Link href={`/reviews/${r.id}`} className="review-row" key={r.id}><div className="file-icon"><FileCheck2 size={17}/></div><div className="review-main"><b>{r.name}</b><span>{r.uploaded_file?.filename} · {bytes(r.uploaded_file?.size_bytes)}</span></div><div className="review-count">{r.datasets?.length||0} tables</div><div className="status-pill">{r.status}</div><ArrowRight size={16}/></Link>)}</div>}</section>
 </div></AppShell>
}
