import { useState } from 'react';
import { UploadCloud, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { uploadDocument } from '../services/api';
import type { UploadResponse } from '../types';
import { useI18n } from '../i18n/I18nContext';

type Status = 'idle' | 'uploading' | 'success' | 'error';

export function FileUpload() {
  const { t } = useI18n();
  const [status, setStatus] = useState<Status>('idle');
  const [message, setMessage] = useState('');
  const [documentId, setDocumentId] = useState<string>('');

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setStatus('uploading');
    setMessage(t('upload.processing'));

    try {
      const response: UploadResponse = await uploadDocument(file);
      setDocumentId(response.document_id);
      setMessage(t('upload.success', { name: file.name }));
      setStatus('success');
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || t('upload.error');
      setMessage(errorMessage);
      setStatus('error');
    } finally {
      if (event.target) event.target.value = '';
    }
  };

  return (
    <div className="border border-ink-700 rounded-xl bg-ink-900 p-6 h-full flex flex-col">
      <p className="font-mono text-xs text-accent tracking-widest uppercase mb-2">{t('upload.eyebrow')}</p>
      <h2 className="font-display text-3xl text-white mb-6">{t('upload.title')}</h2>

      <label
        htmlFor="file-upload"
        className={`flex-1 flex flex-col items-center justify-center gap-3 border border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
          status === 'uploading'
            ? 'border-ink-600 bg-ink-950 cursor-not-allowed'
            : 'border-ink-600 hover:border-accent/60 hover:bg-accent/5'
        }`}
      >
        <input
          id="file-upload"
          type="file"
          accept=".md,.txt,.pdf"
          onChange={handleFileChange}
          disabled={status === 'uploading'}
          className="hidden"
        />
        <UploadCloud className={`w-8 h-8 ${status === 'uploading' ? 'text-slate-600' : 'text-accent'}`} />
        <p className="text-sm text-slate-400">
          {status === 'uploading' ? t('upload.processing') : t('upload.idle')}
        </p>
        <p className="font-mono text-[11px] text-slate-600">{t('upload.formats')}</p>
      </label>

      {status === 'uploading' && (
        <div className="mt-4 flex items-center gap-2 text-accent text-sm">
          <Loader2 className="w-4 h-4 animate-spin" />
          {t('upload.pipeline')}
        </div>
      )}

      {status === 'success' && (
        <div className="mt-4 border border-accent/30 bg-accent/5 rounded-lg p-4">
          <div className="flex items-start gap-2 text-accent text-sm">
            <CheckCircle2 className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <p>{message}</p>
          </div>
          <p className="mt-2 font-mono text-[11px] text-slate-500 break-all">id: {documentId}</p>
        </div>
      )}

      {status === 'error' && (
        <div className="mt-4 flex items-start gap-2 text-red-400 bg-red-950/30 border border-red-900 rounded-lg p-4 text-sm">
          <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <p>{message}</p>
        </div>
      )}
    </div>
  );
}