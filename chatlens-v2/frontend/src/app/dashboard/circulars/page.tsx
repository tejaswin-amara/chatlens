'use client';

import ERPTablePage from '@/components/ERPTablePage';
import { Megaphone } from '@/components/ui/icons';

export default function CircularsPage() {
  return (
    <ERPTablePage
      module="circulars"
      title="Circulars"
      description="Announcements from the ERP system"
      emptyIcon={<Megaphone className="w-10 h-10 text-muted-foreground/30" />}
      emptyTitle="No circulars"
      emptyDescription="Circulars will appear here when published."
    />
  );
}
