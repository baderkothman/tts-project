import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { ProviderInfo } from '../types';
import { SynthesisStudio } from './SynthesisStudio';

const { voices } = vi.hoisted(() => ({ voices: vi.fn() }));
vi.mock('../lib/api', () => ({
  api: {
    voices,
    preview: vi.fn(),
    synthesize: vi.fn(),
  },
}));

const provider = (overrides: Partial<ProviderInfo>): ProviderInfo => ({
  id: 'edge',
  display_name: 'Edge',
  status: 'available',
  capabilities: {
    streaming: true,
    ssml: true,
    phoneme: false,
    native_emotions: false,
    locales: ['ar-SA'],
    formats: ['mp3_24khz'],
    max_chars: 5000,
    notes: '',
  },
  voice_count: 1,
  unavailable_reason: null,
  ...overrides,
});

describe('SynthesisStudio', () => {
  beforeEach(() => voices.mockResolvedValue([]));
  afterEach(cleanup);

  it('selects the first available provider and explains unavailable ones', async () => {
    render(<SynthesisStudio providers={[
      provider({ id: 'groq', display_name: 'Groq', status: 'missing_credentials', unavailable_reason: 'أضف GROQ_API_KEY' }),
      provider({ id: 'edge', display_name: 'Edge' }),
    ]} samples={[]} />);

    expect(screen.getByLabelText('المزوّد')).toHaveValue('edge');
    fireEvent.click(screen.getByText('1 مزوّد غير مفعّل'));
    expect(screen.getByText(/أضف GROQ_API_KEY/)).toBeVisible();
    await waitFor(() => expect(voices).toHaveBeenCalledWith('edge', expect.any(AbortSignal)));
  });

  it('disables actions for whitespace-only text', () => {
    render(<SynthesisStudio providers={[provider({})]} samples={[]} />);
    fireEvent.change(screen.getByLabelText('النص العربي'), { target: { value: '   ' } });
    expect(screen.getByRole('button', { name: /ولّد الصوت/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: /عاين المعالجة/ })).toBeDisabled();
  });
});
