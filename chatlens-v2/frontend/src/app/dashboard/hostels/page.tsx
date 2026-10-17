'use client';

import ERPTablePage from '@/components/ERPTablePage';
import { Building2 } from '@/components/ui/icons';

export default function HostelsPage() {
  return (
    <ERPTablePage
      module="hostels"
      title="Hostel Information"
      description="Hostel allocation data from ERP"
      emptyIcon={<Building2 className="w-10 h-10 text-muted-foreground/30" />}
      emptyTitle="No hostel data"
      emptyDescription="Hostel allocation will appear here."
    />
  );
}
