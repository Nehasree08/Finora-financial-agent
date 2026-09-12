export function compactNumber(value: number) {
  if (!Number.isFinite(value)) return '—';
  return new Intl.NumberFormat('en-IN', { notation: 'compact', maximumFractionDigits: 1 }).format(value);
}
export function integer(value: number) { return new Intl.NumberFormat('en-IN').format(value || 0); }
export function bytes(value = 0) { if (!value) return '0 B'; const units=['B','KB','MB','GB']; const i=Math.floor(Math.log(value)/Math.log(1024)); return `${(value/Math.pow(1024,i)).toFixed(i?1:0)} ${units[i]}`; }
export function date(value?: string) { if (!value) return '—'; return new Date(value).toLocaleString('en-IN', { day:'2-digit', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit' }); }
