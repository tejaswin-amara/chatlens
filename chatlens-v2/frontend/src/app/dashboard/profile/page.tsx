/* eslint-disable @next/next/no-img-element */
'use client';

import { useState } from 'react';
import { useProfile } from '@/hooks/useProfile';
import { Loader2 } from '@/components/ui/icons';
import { triggerHaptic } from '@/lib/fluid-motion';
import { EmptyState } from '@/components/ui/empty-state';

export default function ProfilePage() {
  const [activeTab, setActiveTab] = useState<string | null>(null);
  const {
    data: profileData,
    isLoading: loading,
    error: fetchError,
    mutate,
  } = useProfile();
  const data = (profileData as Record<string, unknown>) || null;
  const error = fetchError ? fetchError.message : null;

  return (
    <div className="flex flex-col gap-6 w-full animate-spring-up">
      <div>
        <h2 className="text-3xl font-semibold tracking-[-0.025em] text-foreground font-heading">
          Profile
        </h2>
        <p className="text-xs text-muted-foreground/90 mt-1 font-normal">
          Manage your academic profile details synced from the ERP.
        </p>
      </div>

      {loading ? (
        <div className="apple-card rounded-[--radius-2xl] min-h-[300px] flex flex-col items-center justify-center p-8 shadow-xl border border-border">
          <Loader2 className="w-8 h-8 text-primary animate-spin mb-4" />
          <span className="text-xs text-muted-foreground font-medium">
            Syncing your profile...
          </span>
        </div>
      ) : error ? (
        <EmptyState
          variant="error"
          description={error}
          action={{ label: 'Retry', onClick: () => mutate() }}
        />
      ) : data ? (
        <div className="apple-card rounded-[--radius-2xl] shadow-2xl border border-border overflow-hidden">
          {/* Profile Header */}
          {(() => {
            const uid = String(data.universityId || '');
            const photo = String(data.photoUrl || '');
            const nameStr = String(data.name || '');

            return (
              <div className="p-6 sm:p-8 border-b border-border bg-surface-2/30 relative">
                <div className="relative z-10 flex flex-col sm:flex-row items-center sm:items-end gap-5">
                  <div className="w-24 h-24 sm:w-28 sm:h-28 rounded-full bg-surface-2 border-2 border-primary/40 shadow-xl flex items-center justify-center text-foreground text-3xl font-bold overflow-hidden relative">
                    {uid ? (
                      <img
                        src={
                          photo.replace(/\s/g, '').startsWith('data:image')
                            ? photo
                            : photo
                              ? `/api/fetch-photo?path=${encodeURIComponent(photo)}`
                              : `/api/fetch-photo?id=${uid}`
                        }
                        alt="Profile"
                        className="w-full h-full object-cover absolute inset-0 z-10"
                        onError={(e) => {
                          e.currentTarget.style.display = 'none';
                        }}
                      />
                    ) : null}
                    <span className="z-0 relative">
                      {nameStr ? nameStr.charAt(0).toUpperCase() : 'U'}
                    </span>
                  </div>
                  <div className="text-center sm:text-left text-foreground pb-1 z-20">
                    <h3 className="text-2xl sm:text-3xl font-bold tracking-tight font-heading">
                      {nameStr || 'Unknown Student'}
                    </h3>
                    <div className="inline-flex items-center gap-2 mt-2 px-3 py-1 bg-surface-2 border border-border rounded-full">
                      <span className="text-xs text-muted-foreground font-mono tracking-wider">
                        ID: {uid || 'N/A'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Profile Details Grid */}
          <div className="p-6 sm:p-8">
            <h4 className="caption-label text-muted-foreground/90 mb-4">
              All Information
            </h4>

            <div>
              {(() => {
                let displayData: Record<string, unknown> = {};

                if (data.extendedProfile) {
                  try {
                    displayData = JSON.parse(data.extendedProfile as string);
                  } catch {}
                } else {
                  displayData = { ...data };
                }

                const ignoredKeys = [
                  'name',
                  'universityId',
                  'photoUrl',
                  'extendedProfile',
                  'success',
                  'rawHtmlLength',
                  'allImages',
                  'allLinks',
                ];
                const allEntries = Object.entries(displayData).filter(
                  ([k]) => !ignoredKeys.includes(k)
                );

                const scalarEntries = allEntries.filter(
                  ([k, v]) =>
                    !Array.isArray(v) &&
                    typeof v !== 'object' &&
                    !k.toLowerCase().includes('photo') &&
                    !String(v).startsWith('http') &&
                    !String(v).startsWith('data:image')
                );
                const arrayEntries = allEntries.filter(([, v]) => {
                  if (!Array.isArray(v) || v.length === 0) return false;
                  if (v.length === 1) {
                    const vals = Object.values(v[0] as Record<string, unknown>);
                    if (
                      vals.some(
                        (val) =>
                          typeof val === 'string' &&
                          (val.toLowerCase().includes('no results found') ||
                            val.toLowerCase().includes('no records') ||
                            val.toLowerCase().includes('no data'))
                      )
                    ) {
                      return false;
                    }
                  }
                  return true;
                });

                const currentTab =
                  activeTab ||
                  (arrayEntries.length > 0 ? arrayEntries[0][0] : null);

                return (
                  <>
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 mb-8">
                      {scalarEntries.map(([k, v]) => (
                        <div
                          key={k}
                          className="flex flex-col p-3 bg-surface-2/40 rounded-[--radius-lg] border border-border hover:border-primary/30 transition-all touch-manipulation"
                        >
                          <span
                            className="text-[9px] font-bold tracking-widest uppercase text-muted-foreground truncate mb-0.5"
                            title={k}
                          >
                            {k.replace(/([A-Z])/g, ' $1').trim()}
                          </span>
                          <span
                            className="text-xs font-semibold text-foreground truncate tracking-tight"
                            title={String(v)}
                          >
                            {String(v) || 'Not Provided'}
                          </span>
                        </div>
                      ))}
                    </div>

                    {arrayEntries.length > 0 && (
                      <div className="mt-8 pt-6 border-t border-border">
                        <div className="flex flex-wrap gap-2 mb-6">
                          {arrayEntries.map(([k]) => (
                            <button
                              key={k}
                              onClick={() => {
                                triggerHaptic('selection');
                                setActiveTab(k);
                              }}
                              className={`px-4 py-2 text-xs font-semibold rounded-full transition-all duration-[--duration-fast] ease-[--ease-spring-default] min-h-[44px] flex items-center cursor-pointer touch-manipulation active:scale-95 ${
                                currentTab === k
                                  ? 'bg-primary text-primary-foreground shadow-md'
                                  : 'bg-surface-2/50 text-muted-foreground hover:text-foreground border border-border hover:border-primary/30'
                              }`}
                            >
                              {k.includes(' ') || k.toLowerCase() === k
                                ? k
                                : k.replace(/([A-Z])/g, ' $1').trim()}
                            </button>
                          ))}
                        </div>

                        {arrayEntries.map(([k, v]: [string, unknown]) => {
                          if (k !== currentTab) return null;
                          const rows = (Array.isArray(v) ? v : []) as Record<
                            string,
                            unknown
                          >[];
                          if (rows.length === 0) return null;

                          return (
                            <div
                              key={k}
                              className="overflow-x-auto rounded-[--radius-xl] border border-border apple-card shadow-xl custom-scrollbar"
                            >
                              <table className="w-full text-left border-collapse">
                                <thead>
                                  <tr className="border-b border-border bg-surface-2/50">
                                    {Object.keys(rows[0]).map((header) => (
                                      <th
                                        key={header}
                                        scope="col"
                                        className="px-4 py-3 caption-label text-muted-foreground whitespace-nowrap"
                                      >
                                        {header}
                                      </th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-border">
                                  {rows.map((row, idx) => (
                                    <tr
                                      key={idx}
                                      className="hover:bg-surface-2 transition-colors"
                                    >
                                      {Object.values(row).map(
                                        (val: unknown, cellIdx) => (
                                          <td
                                            key={cellIdx}
                                            className="px-4 py-3 text-xs text-foreground font-medium whitespace-nowrap tabular-numbers"
                                          >
                                            {typeof val === 'object' &&
                                            val !== null &&
                                            (val as { type?: string }).type ===
                                              'link' ? (
                                              <a
                                                href={
                                                  (val as { url?: string }).url
                                                }
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-primary hover:underline font-semibold"
                                              >
                                                {
                                                  (val as { text?: string })
                                                    .text
                                                }
                                              </a>
                                            ) : (
                                              String(val)
                                            )}
                                          </td>
                                        )
                                      )}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </>
                );
              })()}
            </div>
          </div>
        </div>
      ) : (
        <EmptyState
          title="No profile data"
          description="Profile information will appear once available from the ERP."
        />
      )}
    </div>
  );
}
