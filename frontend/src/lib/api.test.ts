import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, api, audioFromBase64 } from './api';

describe('api client', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('encodes the provider when requesting voices', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await api.voices('provider/with spaces');

    expect(fetchMock).toHaveBeenCalledWith('/api/voices?provider=provider%2Fwith%20spaces', { signal: undefined });
  });

  it('exposes the backend validation message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: { message: 'الصوت غير متاح' } }),
      { status: 400, statusText: 'Bad Request' },
    )));

    await expect(api.preview({
      text: 'اختبار',
      provider: 'edge',
      dialect: null,
      voice_id: null,
      emotion: 'neutral',
      client_t0_ms: 0,
    })).rejects.toEqual(new ApiError('الصوت غير متاح', 400));
  });

  it('decodes base64 audio into a typed blob', () => {
    const blob = audioFromBase64(btoa('audio'));
    expect(blob.type).toBe('audio/mpeg');
    expect(blob.size).toBe(5);
  });
});
