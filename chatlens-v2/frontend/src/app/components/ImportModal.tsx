'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { X, Upload } from 'lucide-react';
import clsx from 'clsx';

interface ImportModalProps {
  open: boolean;
  onClose: () => void;
  onImportComplete: () => void;
  onToast: (message: string, type: 'success' | 'error' | 'info') => void;
  api: {
    uploadFile: (file: File, platform: 'whatsapp' | 'telegram') => Promise<{ status: string; count?: number; error?: string }>;
    checkTelegramStatus: () => Promise<{ authorized: boolean }>;
    sendTelegramCode: (phone: string) => Promise<{ success: boolean; phone_code_hash: string }>;
    verifyTelegramCode: (phone: string, code: string, hash: string) => Promise<{ success: boolean; count?: number }>;
    syncTelegramLive: () => Promise<{ success: boolean; count?: number }>;
  };
}

export default function ImportModal({ open, onClose, onImportComplete, onToast, api }: ImportModalProps) {
  const [modalTab, setModalTab] = useState<'file' | 'live'>('file');
  const [importStatus, setImportStatus] = useState('');
  const [tgPhone, setTgPhone] = useState('');
  const [tgCode, setTgCode] = useState('');
  const [tgHash, setTgHash] = useState('');
  const [tgStep, setTgStep] = useState<'phone' | 'code'>('phone');
  const [tgLoading, setTgLoading] = useState(false);
  const [tgAuthorized, setTgAuthorized] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [open, onClose]);

  // Check Telegram auth when live tab opens
  useEffect(() => {
    if (!open || modalTab !== 'live') return;
    let cancelled = false;
    api.checkTelegramStatus().then((res) => {
      if (!cancelled) setTgAuthorized(res.authorized);
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [open, modalTab, api]);

  const handleFileUpload = useCallback(async (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase();
    let platform: 'whatsapp' | 'telegram';
    if (ext === 'txt') {
      platform = 'whatsapp';
    } else if (ext === 'json') {
      platform = 'telegram';
    } else {
      onToast('Unsupported file type. Use .txt (WhatsApp) or .json (Telegram).', 'error');
      return;
    }

    setImportStatus('Uploading…');
    try {
      const res = await api.uploadFile(file, platform);
      if (res.status === 'ok' || res.status === 'success') {
        setImportStatus(`Imported ${res.count ?? 0} messages`);
        onToast(`Imported ${res.count ?? 0} messages from ${platform}`, 'success');
        onImportComplete();
      } else {
        setImportStatus(res.error || 'Import failed');
        onToast(res.error || 'Import failed', 'error');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload error';
      setImportStatus(msg);
      onToast(msg, 'error');
    }
  }, [api, onToast, onImportComplete]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileUpload(file);
  }, [handleFileUpload]);

  const handleSendCode = async () => {
    setTgLoading(true);
    try {
      const res = await api.sendTelegramCode(tgPhone);
      if (res.success && res.phone_code_hash === 'ALREADY_AUTHORIZED') {
        setTgAuthorized(true);
        setImportStatus('Already connected — you can sync now');
      } else if (res.success) {
        setTgHash(res.phone_code_hash);
        setTgStep('code');
        setImportStatus('Code sent — check your Telegram app');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to send code';
      onToast(msg, 'error');
    } finally {
      setTgLoading(false);
    }
  };

  const handleVerify = async () => {
    setTgLoading(true);
    try {
      const res = await api.verifyTelegramCode(tgPhone, tgCode, tgHash);
      if (res.success) {
        onToast(`Synced ${res.count ?? 0} messages from Telegram`, 'success');
        onImportComplete();
        setTimeout(onClose, 1500);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Verification failed';
      onToast(msg, 'error');
    } finally {
      setTgLoading(false);
    }
  };

  const handleSyncLive = async () => {
    setTgLoading(true);
    try {
      const res = await api.syncTelegramLive();
      if (res.success) {
        onToast(`Synced ${res.count ?? 0} live messages`, 'success');
        onImportComplete();
        setTimeout(onClose, 1500);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Sync failed';
      onToast(msg, 'error');
    } finally {
      setTgLoading(false);
    }
  };

  if (!open) return null;

  const inputClass = 'w-full px-3 py-2 rounded-brand-sm border border-brand-border bg-brand-card text-sm focus:border-brand-accent outline-none';
  const btnClass = 'w-full py-2 rounded-brand-sm bg-brand-accent/10 border border-brand-accent/30 text-brand-accent text-sm font-medium hover:bg-brand-accent/20 disabled:opacity-50 spring-click';

  return (
    <div
      className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-brand-bg border border-brand-border rounded-brand w-[90%] max-w-[400px] p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Import Data</h2>
          <button onClick={onClose} className="spring-click text-brand-text-dim hover:text-brand-text">
            <X size={18} />
          </button>
        </div>

        {/* Tab Bar */}
        <div className="flex gap-2 mb-4">
          {(['file', 'live'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setModalTab(tab)}
              className={clsx(
                'px-3 py-1 rounded text-sm font-medium',
                modalTab === tab ? 'bg-brand-accent/15 text-brand-accent' : 'text-brand-text-dim'
              )}
            >
              {tab === 'file' ? 'File Upload' : 'Telegram Live'}
            </button>
          ))}
        </div>

        {/* File Upload Tab */}
        {modalTab === 'file' && (
          <div>
            <p className="text-sm text-brand-text-dim mb-3">
              Upload a WhatsApp export (.txt) or Telegram export (.json).
            </p>

            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={clsx(
                'border-2 border-dashed rounded-brand-sm p-8 flex flex-col items-center justify-center gap-2 cursor-pointer transition-colors',
                dragOver ? 'border-brand-accent bg-brand-accent/5' : 'border-brand-border'
              )}
            >
              <Upload size={24} className="text-brand-text-dim" />
              <span className="text-sm text-brand-text-dim">Click or drag file here</span>
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.json"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFileUpload(file);
                e.target.value = '';
              }}
            />
          </div>
        )}

        {/* Telegram Live Tab */}
        {modalTab === 'live' && (
          <div>
            {tgAuthorized ? (
              <div>
                <p className="text-sm text-brand-text-dim mb-3">You are already connected.</p>
                <button className={btnClass} disabled={tgLoading} onClick={handleSyncLive}>
                  {tgLoading ? 'Syncing…' : 'Sync Live Messages'}
                </button>
              </div>
            ) : tgStep === 'phone' ? (
              <div className="flex flex-col gap-3">
                <input
                  type="tel"
                  placeholder="Phone number (e.g. +1234567890)"
                  value={tgPhone}
                  onChange={(e) => setTgPhone(e.target.value)}
                  disabled={tgLoading}
                  className={inputClass}
                />
                <button className={btnClass} disabled={tgLoading || !tgPhone.trim()} onClick={handleSendCode}>
                  {tgLoading ? 'Sending…' : 'Send Code'}
                </button>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                <input
                  type="text"
                  placeholder="Enter verification code"
                  value={tgCode}
                  onChange={(e) => setTgCode(e.target.value)}
                  disabled={tgLoading}
                  className={inputClass}
                />
                <button className={btnClass} disabled={tgLoading || !tgCode.trim()} onClick={handleVerify}>
                  {tgLoading ? 'Verifying…' : 'Verify & Sync'}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Status Line */}
        {importStatus && (
          <p className="text-center text-sm text-brand-accent mt-4">{importStatus}</p>
        )}
      </div>
    </div>
  );
}
