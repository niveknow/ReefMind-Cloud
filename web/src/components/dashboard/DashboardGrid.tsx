import React from 'react';
import { DashboardWidget } from '../../types/dashboard';
import { WidgetRenderer } from './WidgetRenderer';

interface DashboardGridProps {
  layout: DashboardWidget[];
  data: any;
}

const COL_MAP: Record<number, string> = {
  1: 'col-span-1', 2: 'col-span-2', 3: 'col-span-3', 4: 'col-span-4',
  5: 'col-span-5', 6: 'col-span-6', 7: 'col-span-7', 8: 'col-span-8',
  9: 'col-span-9', 10: 'col-span-10', 11: 'col-span-11', 12: 'col-span-12',
};

const ROW_MAP: Record<number, string> = {
  1: 'row-span-1', 2: 'row-span-2', 3: 'row-span-3',
  4: 'row-span-4', 5: 'row-span-5', 6: 'row-span-6',
};

export const DashboardGrid: React.FC<DashboardGridProps> = ({ layout, data }) => {
  // Calculate maximum grid dimensions
  const maxRow = Math.max(...layout.map(w => w.y + w.h), 6);
  const gridRows = Array.from({ length: maxRow }, (_, i) => i);

  return (
    <div className="grid grid-cols-12 gap-4 auto-rows-auto">
      {layout.map(widget => {
        const colClass = COL_MAP[widget.w] || 'col-span-6';
        const rowClass = ROW_MAP[widget.h] || 'row-span-1';

        return (
          <div
            key={widget.i}
            className={`${colClass} ${rowClass}`}
          >
            <WidgetRenderer widget={widget} data={data} />
          </div>
        );
      })}
    </div>
  );
};
