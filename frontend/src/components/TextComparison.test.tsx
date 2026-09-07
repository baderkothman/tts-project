import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { TextComparison } from './TextComparison';

describe('TextComparison', () => {
  it('shows only stages that changed the text', () => {
    render(<TextComparison result={{
      original: 'API 3',
      processed: 'إيه بي آي ثلاثة',
      changed: true,
      stages: [
        { stage_name: 'numbers', before: '3', after: 'ثلاثة', changed: true, duration_ms: 0.2 },
        { stage_name: 'dates', before: '', after: '', changed: false, duration_ms: 0.1 },
      ],
    }} />);

    expect(screen.getByText('numbers')).toBeVisible();
    expect(screen.queryByText('dates')).not.toBeInTheDocument();
    expect(screen.getByText('إيه بي آي ثلاثة')).toBeVisible();
  });
});
