import { Scale, FileDown } from 'lucide-react'
import { reportUrl, legalReportUrl } from '../lib/api.js'

export default function LegalReportButtons({ caseId }) {
  return (
    <div className="w-full space-y-2">
      <a
        href={reportUrl(caseId)}
        download
        className="w-full inline-flex items-center justify-center gap-2 rounded-lg border border-trace/40 bg-trace/10 text-trace text-xs font-medium py-2.5 hover:bg-trace/20 transition-colors"
      >
        <FileDown size={14} /> Download Forensic Report (PDF)
      </a>
      <div className="grid grid-cols-2 gap-2">
        <a
          href={legalReportUrl(caseId, 'us')}
          download
          className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-wire/40 bg-wire/10 text-wire text-xs font-medium py-2.5 hover:bg-wire/20 transition-colors"
        >
          <Scale size={13} /> Legal Report (US)
        </a>
        <a
          href={legalReportUrl(caseId, 'eu')}
          download
          className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-wire/40 bg-wire/10 text-wire text-xs font-medium py-2.5 hover:bg-wire/20 transition-colors"
        >
          <Scale size={13} /> Legal Report (EU)
        </a>
      </div>
    </div>
  )
}
