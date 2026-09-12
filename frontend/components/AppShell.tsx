'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Activity, BarChart3, BrainCircuit, Database, FileSearch, FolderKanban, LayoutDashboard, Radar, Settings2, ShieldCheck, Sparkles, UploadCloud } from 'lucide-react';
import AuditChat from './AuditChat';

const nav = [
  { href:'/dashboard', label:'Command center', icon:LayoutDashboard },
  { href:'/reviews', label:'Review vault', icon:FolderKanban },
  { href:'/upload', label:'Ingest dataset', icon:UploadCloud },
  { href:'/compare', label:'Compare universes', icon:FileSearch },
];
const audit = [
  { key:'universe', label:'Data universe', icon:Database },
  { key:'validation', label:'Validation', icon:ShieldCheck },
  { key:'variance', label:'Variance', icon:BarChart3 },
  { key:'ratios', label:'Ratios', icon:Activity },
  { key:'anomalies', label:'Anomalies', icon:Radar },
  { key:'ai', label:'AI review', icon:BrainCircuit },
];

export default function AppShell({ children, reviewId }: { children: React.ReactNode; reviewId?: number }) {
  const pathname = usePathname();
  const link = (base: string) => reviewId ? `${base}${base.includes('?') ? '&' : '?'}reviewId=${reviewId}` : base;
  return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Sparkles size={18}/></div><div><b>FINORA</b><span>audit intelligence</span></div></div>
      <div className="live"><i/> LIVE AUDIT CORE <span>v1</span></div>
      <nav className="nav">{nav.map(({href,label,icon:Icon}) => <Link key={href} className={pathname===href?'active':''} href={href}><Icon size={17}/><span>{label}</span></Link>)}</nav>
      <div className="nav-label">AUDIT LAYERS</div>
      <nav className="nav compact">{audit.map(({key,label,icon:Icon}) => <Link key={label} className={pathname==='/audit' && key==='universe'?'active':''} href={link(`/audit?layer=${key}`)}><Icon size={16}/><span>{label}</span></Link>)}</nav>
      <div className="sidebar-bottom"><Link href="#" className="settings"><Settings2 size={16}/> Workspace settings</Link></div>
    </aside>
    <main className="main"><header className="topbar"><div><div className="crumb">FINORA / {pathname?.slice(1).toUpperCase() || 'COMMAND'}</div><h1>Financial intelligence, without the black box.</h1></div><div className="top-actions"><div className="status"><i/> Engine online</div><div className="avatar">N</div></div></header>{children}<AuditChat reviewId={reviewId}/></main>
  </div>
}
