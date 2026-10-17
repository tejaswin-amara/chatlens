'use client';

import ERPTablePage from '@/components/ERPTablePage';
import { BookOpen } from '@/components/ui/icons';

export default function LibraryPage() {
  return (
    <ERPTablePage
      module="library"
      title="Library"
      description="Library records from ERP"
      emptyIcon={<BookOpen className="w-10 h-10 text-muted-foreground/30" />}
      emptyTitle="No library data"
      emptyDescription="Library records will appear here."
    />
  );
}
