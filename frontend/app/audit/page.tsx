'use client';
import { Suspense, useEffect, useState } from 'react';
import { Activity, AlertTriangle, BarChart3, BrainCircuit, Database, Radar, ShieldCheck } from 'lucide-react';
import { useSearchParams } from 'next/navigation';
import AppShell from '../../components/AppShell';
import { api, Review } from '../../lib/api';

const labels: Record<string, string> = { universe: 'Data universe', validation: 'Validation', variance: 'Variance', ratios: 'Ratios', anomalies: 'Anomalies', ai: 'AI review' };
const format = (value: any) => typeof value === 'number' ? value.toLocaleString('en-US', { maximumFractionDigits: 2 }) : value ?? '-';

function AuditContent() {
  const params = useSearchParams();
  const layer = params.get('layer') || 'universe';
  const requestedId = params.get('reviewId');
  const [reviews, setReviews] = useState<Review[]>([]);
  const [reviewId, setReviewId] = useState(requestedId || '');
  const [audit, setAudit] = useState<any>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.reviews().then(result => {
      setReviews(result.items || []);
      if (!requestedId && result.items?.[0]) setReviewId(String(result.items[0].id));
    }).catch(error => setError(error.message));
  }, [requestedId]);

  useEffect(() => {
    if (!reviewId) return;
    setAudit(null);
    api.audit(Number(reviewId)).then(result => setAudit(result.audit)).catch(error => setError(error.message));
  }, [reviewId]);

  const validation = audit?.validation;
  return <AppShell reviewId={reviewId ? Number(reviewId) : undefined}><div className="page">
    <div className="section-head big"><div><span className="eyebrow"><ShieldCheck size={13}/> AUDIT LAYERS</span><h2>{labels[layer] || 'Audit workspace'}</h2><p>Evidence-grounded analysis built from the selected persisted review.</p></div><select value={reviewId} onChange={event => setReviewId(event.target.value)}><option value="">Choose review...</option>{reviews.map(review => <option key={review.id} value={review.id}>{review.name}</option>)}</select></div>
    {error && <div className="error">{error}</div>}
    {!audit && !error && <div className="loading-screen"><div className="loader-orb"/><b>Running audit layer...</b></div>}
    {audit && layer === 'universe' && <><div className="metric-grid"><div className="metric"><span>REVIEW</span><strong>#{audit.review.id}</strong><small>{audit.review.name}</small></div><div className="metric"><span>MISSING</span><strong>{format(validation.missing_values)}</strong><small>fields requiring review</small></div><div className="metric"><span>DUPLICATES</span><strong>{format(validation.duplicate_rows)}</strong><small>duplicate source rows</small></div><div className="metric"><span>ANOMALIES</span><strong>{audit.anomalies.length}</strong><small>numeric signals</small></div></div><section className="panel"><div className="panel-head"><div><span className="eyebrow"><Database size={13}/> SOURCE UNIVERSE</span><h3>{audit.review.name}</h3></div></div><div className="compare-note"><b>Source locked</b><p>The audit layers below operate on this persisted review and do not invent values outside its uploaded evidence.</p></div></section></>}
    {audit && layer === 'validation' && <section className="panel"><div className="panel-head"><div><span className="eyebrow"><ShieldCheck size={13}/> VALIDATION</span><h3>Integrity and mathematical checks</h3></div></div><div className="compare-hero"><div><span>MISSING VALUES</span><strong>{format(validation.missing_values)}</strong></div><div><span>DUPLICATE ROWS</span><strong>{format(validation.duplicate_rows)}</strong></div><div><span>NULLABLE FIELDS</span><strong>{validation.nullable_fields.length}</strong></div><div><span>EMPTY FIELDS</span><strong>{validation.empty_fields.length}</strong></div></div><div className="signal-list">{[...validation.nullable_fields, ...validation.empty_fields].map((field: string) => <div className="signal" key={field}><span>!</span><p>{field} requires a completeness review.</p></div>)}{audit.math_checks.map((check: any) => <div className="signal" key={check.check}><span>{check.status === 'pass' ? 'OK' : '!'}</span><p><b>{check.check}</b> — {check.matching_rows}/{check.checked_rows} rows reconcile.{check.evidence.length ? ` Example row ${check.evidence[0].row} differs by ${format(check.evidence[0].difference)}.` : ''}</p></div>)}{!validation.nullable_fields.length && !validation.empty_fields.length && !audit.math_checks.length && <div className="empty"><ShieldCheck size={22}/><b>No structural validation warnings</b></div>}</div></section>}
    {audit && layer === 'variance' && <section className="panel"><div className="panel-head"><div><span className="eyebrow"><BarChart3 size={13}/> VARIANCE</span><h3>Year-over-year and entity movement</h3></div></div>{audit.year_over_year.map((item: any) => <div className="delta-row" key={`yoy-${item.metric}`}><div className="delta-name"><b>{item.metric}</b><small>{item.previous_year} to {item.current_year}</small></div><div><b>{format(item.previous_value)}</b><small>prior year</small></div><div><b>{format(item.current_value)}</b><small>current year</small></div><div className={(item.change_percent || 0) >= 0 ? 'up' : 'down'}>{item.change_percent == null ? '-' : `${item.change_percent.toFixed(1)}%`}</div></div>)}{audit.variance.map((item: any) => <div className="delta-row" key={item.metric}><div className="delta-name"><b>{item.metric}</b><small>grouped by {item.entity_column}</small></div><div><b>{item.highest.entity}</b><small>{format(item.highest.value)}</small></div><div><b>{item.lowest.entity}</b><small>{format(item.lowest.value)}</small></div><div className="up">{format(item.difference)}</div></div>)}{!audit.year_over_year.length && !audit.variance.length && <div className="empty"><BarChart3 size={22}/><b>No variance available</b></div>}</section>}
    {audit && layer === 'ratios' && <section className="panel"><div className="panel-head"><div><span className="eyebrow"><Activity size={13}/> RATIOS</span><h3>Grounded financial ratios</h3></div></div>{audit.ratios.length ? audit.ratios.map((ratio: any) => <div className="delta-row" key={ratio.name}><div className="delta-name"><b>{ratio.name.replaceAll('_', ' ')}</b><small>{format(ratio.numerator)} / {format(ratio.denominator)}</small></div><div><b>{format(ratio.value * 100)}%</b><small>percentage</small></div></div>) : <div className="empty"><Activity size={22}/><b>No compatible financial concepts found</b><span>Ratios appear when the uploaded data contains the required fields.</span></div>}</section>}
    {audit && layer === 'anomalies' && <section className="panel"><div className="panel-head"><div><span className="eyebrow"><Radar size={13}/> ANOMALIES</span><h3>Numeric review signals</h3></div></div>{audit.anomalies.length ? audit.anomalies.map((item: any) => <div className="delta-row" key={item.field}><div className="delta-name"><b>{item.field}</b><small>{item.count} outlier(s)</small></div><div><b>{format(item.max_abs_z)}σ</b><small>maximum distance</small></div><div className="up"><AlertTriangle size={16}/></div></div>) : <div className="empty"><Radar size={22}/><b>No numeric anomalies detected</b></div>}</section>}
    {audit && layer === 'ai' && <section className="panel"><div className="panel-head"><div><span className="eyebrow"><BrainCircuit size={13}/> REVIEW COMMENTS</span><h3>Evidence-aware findings</h3></div><button className="ghost" onClick={() => { const report = [`FINORA AUDIT REVIEW`, `Review: ${audit.review.name}`, ``, ...audit.review_comments, ``, ...audit.ai_review].join('\n'); const blob = new Blob([report], { type: 'text/plain' }); const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = `finora-audit-review-${audit.review.id}.txt`; anchor.click(); URL.revokeObjectURL(url); }}>Download report</button></div>{audit.review_comments.map((finding: string, index: number) => <div className="signal" key={`comment-${index}`}><span>!</span><p>{finding}</p></div>)}{audit.ai_review.map((finding: string, index: number) => <div className="signal" key={`summary-${index}`}><span>{String(index + 1).padStart(2, '0')}</span><p>{finding}</p></div>)}</section>}
  </div></AppShell>;
}

export default function Audit() {
  return <Suspense fallback={<div className="loading-screen"><div className="loader-orb"/><b>Loading audit workspace...</b></div>}><AuditContent /></Suspense>;
}
