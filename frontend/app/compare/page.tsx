'use client';
import { useEffect, useState } from 'react';
import { ArrowRight, GitCompare, Layers3, Sparkles } from 'lucide-react';
import AppShell from '../../components/AppShell';
import { api, ComparisonOptions, Review } from '../../lib/api';

function number(value: number | null) {
  return value == null ? '-' : value.toLocaleString('en-US', { maximumFractionDigits: 2 });
}

function reviewLabel(name: string) {
  return name.replace(/^Review\s*[—-]\s*/i, '').replace(/\.csv$/i, '').replace(/\.xlsx?$/i, '');
}

export default function Compare() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [reviewId, setReviewId] = useState('');
  const [options, setOptions] = useState<ComparisonOptions>({ entity_columns: [], metric_columns: [] });
  const [entityColumn, setEntityColumn] = useState('');
  const [left, setLeft] = useState('');
  const [right, setRight] = useState('');
  const [metric, setMetric] = useState('');
  const [data, setData] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const entities = options.entity_columns.find(column => column.name === entityColumn)?.entities || [];

  useEffect(() => {
    api.reviews().then(result => {
      const items = result.items || [];
      setReviews(items);
      if (items[0]) setReviewId(String(items[0].id));
    }).catch(error => setError(error.message));
  }, []);

  useEffect(() => {
    if (!reviewId) return;
    setData(null);
    api.comparisonOptions(Number(reviewId)).then(result => {
      setOptions(result);
      setEntityColumn(result.entity_columns[0]?.name || '');
      setMetric('__all__');
    }).catch(error => setError(error.message));
  }, [reviewId]);

  useEffect(() => {
    const nextEntities = options.entity_columns.find(column => column.name === entityColumn)?.entities || [];
    setLeft(nextEntities[0] || '');
    setRight(nextEntities[1] || '');
  }, [entityColumn, options]);

  async function run() {
    if (!reviewId || !entityColumn || !metric || !left || !right || left === right) return;
    setBusy(true);
    setError('');
    try {
      const result = await api.compareWithin(Number(reviewId), entityColumn, metric, left, right);
      setData(result.comparison);
    } catch (error: any) {
      setError(error.message);
    } finally {
      setBusy(false);
    }
  }

  return <AppShell><div className="page">
    <div className="section-head big"><div><span className="eyebrow"><GitCompare size={13}/> WITHIN-DATASET INTELLIGENCE</span><h2>Compare the companies inside one dataset.</h2><p>Select a source dataset, identify its company field, and compare two companies on any discovered financial metric.</p></div></div>
    <section className="compare-pick">
      <div><label>SOURCE DATASET</label><select value={reviewId} onChange={event => setReviewId(event.target.value)}><option value="">Choose dataset...</option>{reviews.map(review => <option key={review.id} value={review.id}>{reviewLabel(review.name)}</option>)}</select></div>
      <div><label>ITEM FIELD</label><select value={entityColumn} onChange={event => setEntityColumn(event.target.value)}><option value="">Choose field...</option>{options.entity_columns.map(column => <option key={column.name} value={column.name}>{column.name}</option>)}</select></div>
      <div><label>METRICS</label><select value={metric} onChange={event => setMetric(event.target.value)}><option value="">Choose metrics...</option><option value="__all__">All metrics ({options.metric_columns.length})</option>{options.metric_columns.map(column => <option key={column} value={column}>{column}</option>)}</select></div>
      <div className="compare-glyph"><GitCompare size={20}/></div>
      <div><label>ITEM A</label><select value={left} onChange={event => setLeft(event.target.value)}><option value="">Choose item...</option>{entities.map(entity => <option key={entity} value={entity}>{entity}</option>)}</select></div>
      <div><label>ITEM B</label><select value={right} onChange={event => setRight(event.target.value)}><option value="">Choose item...</option>{entities.map(entity => <option key={entity} value={entity}>{entity}</option>)}</select></div>
      <button className="primary" disabled={busy || !reviewId || !entityColumn || !metric || !left || !right || left === right} onClick={run}>{busy ? 'Comparing...' : 'Compare items'} <ArrowRight size={15}/></button>
    </section>
    {error && <div className="error">{error}</div>}
    {data && <><div className="compare-hero"><div><span>METRICS</span><strong>{data.metrics?.length || 1}</strong></div><div><span>ITEM A</span><strong>{data.left.entity}</strong></div><div><span>ITEM B</span><strong>{data.right.entity}</strong></div><div><span>ENTITY FIELD</span><strong>{data.entity_column}</strong></div></div><div className="compare-grid"><section className="panel"><div className="panel-head"><div><span className="eyebrow">COMPARISON MATRIX</span><h3>All financial metrics</h3></div><Sparkles size={16}/></div>{data.metrics ? data.metrics.map((item: any) => <div className="delta-row" key={item.metric}><div className="delta-name"><b>{item.metric}</b><small>{item.left.count} vs {item.right.count} rows</small></div><div><b>{number(item.left.sum)}</b><small>{item.left.entity} total</small></div><div><b>{number(item.right.sum)}</b><small>{item.right.entity} total</small></div><div className={(item.right.sum || 0) >= (item.left.sum || 0) ? 'up' : 'down'}>{item.left.sum != null && item.right.sum != null ? number(item.right.sum - item.left.sum) : '-'}</div></div>) : <><div className="delta-row"><div className="delta-name"><b>{data.metric}</b><small>{data.left.count} vs {data.right.count} matching rows</small></div><div><b>{number(data.left.sum)}</b><small>item A total</small></div><div><b>{number(data.right.sum)}</b><small>item B total</small></div><div className="up">{number(data.difference)}</div></div></>}</section><section className="panel"><div className="panel-head"><div><span className="eyebrow">DATASET SCOPE</span><h3>One source, two items</h3></div><Layers3 size={16}/></div><div className="compare-note"><b>Complete metric coverage</b><p>{data.left.entity} and {data.right.entity} are selected from the same persisted dataset. Every discovered numeric metric is shown in the comparison matrix.</p></div></section></div></>}
  </div></AppShell>;
}